from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, urllib.request

ROOT=Path(".")
RELEASE_ID="0.7.9-beta.19-accountsync11"
GAME_BUILD="0.7.9-beta.19"
CLOUD_COMMIT="b85f96051bf7e220fcc26b7bbde6abe23d24864d"
RAW_BASE=f"https://raw.githubusercontent.com/FFDevelopment/afewbuds-cloud-test/{CLOUD_COMMIT}/"

EXPECTED_GIT_BLOBS={
    "index-cloudtest10.pck":"63f51e1ef4cdbed39165bb7b62b2122d4964e31c",
    "index.html":"03f3299f174a6ca05c37a86490b5c70fd0b8c8aa",
    "shared/afb-cloud-accountsync10.js":"78d39b5257bfeeb8a2e3fe5042b684d1321fb941",
}

def download(path):
    req=urllib.request.Request(RAW_BASE+path,headers={"User-Agent":"AFewBuds-accountsync11-promoter"})
    with urllib.request.urlopen(req,timeout=120) as response:
        return response.read()

def git_blob_sha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def pinned(path):
    data=download(path)
    actual=git_blob_sha(data)
    expected=EXPECTED_GIT_BLOBS[path]
    if actual != expected:
        raise RuntimeError(f"Pinned cloudtest40 source changed for {path}: {actual} != {expected}")
    return data

# Pull the exact cloudtest40 runtime the user confirmed boots and works.
pck=pinned("index-cloudtest10.pck")
cloud_html=pinned("index.html").decode("utf-8")
cloud_sync=pinned("shared/afb-cloud-accountsync10.js").decode("utf-8")

(ROOT/"index-accountsync11.pck").write_bytes(pck)
shutil.copy2(ROOT/"index-accountsync10.js",ROOT/"index-accountsync11.js")
(ROOT/"shared/afb-cloud-accountsync11.js").write_text(cloud_sync)

# Convert the tested cloud shell into the production/tester shell while preserving
# the transactional updater and its boot confirmation / rollback hooks.
html=cloud_html
html=re.sub(r"<title>AFewBuds Cloud Test [^<]+</title>",f"<title>AFewBuds {GAME_BUILD}</title>",html,count=1)
html=html.replace(
    'const AFB_TEST_RELEASE = "0.7.9-beta.19-cloudtest.40";',
    f'const AFB_TEST_RELEASE = "{RELEASE_ID}";'
)
html=html.replace(
    'const AFB_TEST_TITLE = "AFewBuds Cloud Test v0.7.9-beta.19";',
    f'const AFB_TEST_TITLE = "AFewBuds {GAME_BUILD}";'
)

config_script='\t\t<script src="shared/config.js"></script>'
if '<script src="shared/afb-updater.js"></script>' not in html:
    if config_script not in html:
        raise RuntimeError("config script anchor missing")
    html=html.replace(config_script,'\t\t<script src="shared/afb-updater.js"></script>\n'+config_script,1)

html=re.sub(
    r'<script src="shared/afb-cloud-accountsync\d+\.js\?v=[^"]+"></script>',
    f'<script src="shared/afb-cloud-accountsync11.js?v={RELEASE_ID}"></script>',
    html,count=1
)
html=re.sub(
    r'<script src="index-accountsync\d+\.js\?v=[^"]+"></script>',
    f'<script src="index-accountsync11.js?v={RELEASE_ID}"></script>',
    html,count=1
)

pck_size=(ROOT/"index-accountsync11.pck").stat().st_size
wasm_size=(ROOT/"index.wasm").stat().st_size
m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
if not m:
    raise RuntimeError("GODOT_CONFIG missing")
cfg=m.group(1)
cfg=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-accountsync11.pck":{pck_size},"index.wasm":{wasm_size}}}',cfg,count=1)
cfg=re.sub(r'"mainPack":"[^"]*"','"mainPack":"index-accountsync11.pck"',cfg,count=1)
cfg=re.sub(r'"serviceWorker":"[^"]*"','"serviceWorker":"index.service.worker.js"',cfg,count=1)
html=html[:m.start(1)]+cfg+html[m.end(1):]

# Password reset links must return to the site where the request originated.
old_reset_body='body:JSON.stringify({username:String(username || \'\').trim()})'
new_reset_body='body:JSON.stringify({username:String(username || \'\').trim(),return_url:location.origin+location.pathname})'
if old_reset_body not in html:
    raise RuntimeError("password reset request anchor missing")
html=html.replace(old_reset_body,new_reset_body,1)

# Re-enable the production updater's game-start watchdog.
launch_anchor="\tdocument.getElementById('afb-account-gate').hidden = true;\n\tafbLoadTracker();"
launch_replacement="\tdocument.getElementById('afb-account-gate').hidden = true;\n\tif (window.AFB_UPDATER) AFB_UPDATER.notifyGameStarting();\n\tafbLoadTracker();"
if launch_anchor not in html:
    raise RuntimeError("launch updater hook anchor missing")
html=html.replace(launch_anchor,launch_replacement,1)

engine_anchor="\t}}).then(() => { setStatusMode('hidden'); }, (error) => { displayFailureNotice(error); });"
engine_replacement="\t}}).then(() => { setStatusMode('hidden'); if (window.AFB_UPDATER) AFB_UPDATER.markGameReady(); }, (error) => { if (window.AFB_UPDATER) AFB_UPDATER.markGameFailure(error); displayFailureNotice(error); });"
if engine_anchor not in html:
    raise RuntimeError("engine updater hook anchor missing")
html=html.replace(engine_anchor,engine_replacement,1)

standalone='''(async function afbStandaloneBoot(){
\t// Standalone cloud-test never uses the legacy web updater.
\t// Remove old registrations/caches left by earlier test builds, then boot directly.
\ttry {
\t\tif ('serviceWorker' in navigator) {
\t\t\tconst regs = await navigator.serviceWorker.getRegistrations();
\t\t\tawait Promise.all(regs.map(r => r.unregister()));
\t\t}
\t\tif ('caches' in window) {
\t\t\tconst keys = await caches.keys();
\t\t\tawait Promise.all(keys.map(k => caches.delete(k)));
\t\t}
\t} catch (e) {
\t\tconsole.warn('AFewBuds cloud-test cache cleanup skipped.', e);
\t}
\tawait afbBootAccountGate();
})();'''
production='''(async function afbPrelaunch(){
\ttry {
\t\tif (window.AFB_UPDATER) await AFB_UPDATER.boot();
\t} catch (error) {
\t\tconsole.warn('AFewBuds updater unavailable; starting installed build.', error);
\t\tconst overlay = document.getElementById('afb-prelaunch');
\t\tif (overlay) overlay.hidden = true;
\t}
\tawait afbBootAccountGate();
})();'''
if standalone not in html:
    raise RuntimeError("standalone boot block missing")
html=html.replace(standalone,production,1)

if "Cloud Test" in html or "Standalone cloud-test" in html:
    raise RuntimeError("cloud-test wording remains in production shell")
required=[
    '<script src="shared/afb-updater.js"></script>',
    'index-accountsync11.pck',
    'index-accountsync11.js',
    'shared/afb-cloud-accountsync11.js',
    '"serviceWorker":"index.service.worker.js"',
    'AFB_UPDATER.notifyGameStarting()',
    'AFB_UPDATER.markGameReady()',
    'AFB_UPDATER.markGameFailure(error)',
    'async function afbPrelaunch()',
    'return_url:location.origin+location.pathname',
    'id="afb-leaderboard-modal"',
    'window.AFB_LEADERBOARD',
    'id="afb-account-settings-modal"',
    'Forgot password?'
]
for needle in required:
    if needle not in html:
        raise RuntimeError("production shell missing "+needle)

(ROOT/"index.html").write_text(html)

(ROOT/"BUILD_VERSION.txt").write_text(
    f"AFewBuds game build: {GAME_BUILD}\n"
    f"Web release: {RELEASE_ID}\n"
    "Updater protocol: 1\n"
)

(ROOT/"RELEASE_NOTES_ACCOUNTSYNC11.txt").write_text(f"""AFewBuds {RELEASE_ID}

Production/tester promotion of the validated cloudtest40 build.

- Preserves all accountsync10 save/account compatibility.
- Hidden Wall Stash: $3,250, 1,000g protected/sellable storage replacing the vault.
- Account settings under Settings > Account:
  username availability/change, email/update preference, and password change.
- Forgot-password recovery via verified email with 30-minute, single-use reset links.
- Global phone Leaderboard on the main phone screen.
- Lifetime and Weekly rankings, Top 5 / Top 25, personal rank, and public career cards.
- Leaderboard stats: revenue, sales, dealer sales, harvests, hybrids, raids survived,
  days played, and career score.
- Weekly leaderboard resets Monday at 12:00 AM America/New_York.
- Leaderboard reporting occurs only after successful cloud saves and cannot block saves.
- Transactional updater preserved: full-file SHA-256 verification, atomic activation,
  boot confirmation, and automatic rollback to accountsync10 on startup failure.
""")

files=[
    "index.html",
    "index-accountsync11.js",
    "index-accountsync11.pck",
    "index.wasm",
    "index.audio.worklet.js",
    "index.audio.position.worklet.js",
    "index.offline.html",
    "index.icon.png",
    "index.apple-touch-icon.png",
    "index.png",
    "index.manifest.json",
    "index.144x144.png",
    "index.180x180.png",
    "index.192x192.png",
    "index.512x512.png",
    "index.service.worker.js",
    "afewbuds-update.html",
    "shared/config.js",
    "shared/afb-api.js",
    "shared/afb-cloud-accountsync11.js",
    "shared/afb-updater.js",
    "shared/afb-tracker.js",
    "shared/style.css",
    "account/index.html",
    "admin/index.html",
]
manifest=[]
for name in files:
    data=(ROOT/name).read_bytes()
    manifest.append({"path":name,"size":len(data),"sha256":hashlib.sha256(data).hexdigest()})

version={
    "updater_protocol":1,
    "release_id":RELEASE_ID,
    "game_build":GAME_BUILD,
    "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    "web_features":[
        "single-account-career",
        "cross-device-cloud-sync",
        "direct-godot-cloud-restore",
        "silent-background-sync",
        "phone-manual-save",
        "manual-save-toast",
        "safe-sleep-quit",
        "portable-ui-glyphs",
        "persistent-admin-session",
        "claim-all-rewards",
        "highlighted-phone-hud-button",
        "reeves-8000-protection-balance",
        "reeves-pay-half-full-refuse",
        "lay-low-lights-down",
        "heat-state-machine-fixes",
        "persistent-enforcement-report",
        "force-reeves-debug-removed",
        "customer-traffic-fallback",
        "stale-customer-runtime-recovery",
        "hidden-wall-stash",
        "account-settings",
        "password-recovery",
        "global-leaderboard",
        "weekly-lifetime-rankings",
        "transactional-updater"
    ],
    "files":manifest
}
(ROOT/"version.json").write_text(json.dumps(version,indent=2)+"\n")

integrity={
    "release_id":RELEASE_ID,
    "game_build":GAME_BUILD,
    "source_cloud_commit":CLOUD_COMMIT,
    "source_cloud_pck_blob":EXPECTED_GIT_BLOBS["index-cloudtest10.pck"],
    "main_pack":"index-accountsync11.pck",
    "main_pack_size":pck_size,
    "main_pack_sha256":next(x["sha256"] for x in manifest if x["path"]=="index-accountsync11.pck"),
    "previous_release":"0.7.9-beta.19-accountsync10",
    "rollback_pack":"index-accountsync10.pck",
    "updater_protocol":1,
    "release_files":len(manifest)
}
(ROOT/"ACCOUNTSYNC11_INTEGRITY.json").write_text(json.dumps(integrity,indent=2)+"\n")
print(json.dumps(integrity,indent=2))
