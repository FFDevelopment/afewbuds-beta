from pathlib import Path
import hashlib, json, re
from datetime import datetime, timezone
import shutil

RELEASE_ID="0.7.9-beta.19-accountsync1"
GAME_BUILD="0.7.9-beta.19"
ROOT=Path(".")
PCK_SRC=ROOT/"cloud-test/index-system-restore2.pck"
JS_SRC=ROOT/"cloud-test/index.js"
CLOUD_SRC=ROOT/"cloud-test/shared/afb-cloud.js"

PCK_DST=ROOT/"index-accountsync1.pck"
JS_DST=ROOT/"index-accountsync1.js"
CLOUD_DST=ROOT/"shared/afb-cloud-accountsync1.js"

for p in (PCK_SRC, JS_SRC, CLOUD_SRC):
    if not p.exists():
        raise SystemExit(f"Missing validated test asset: {p}")

shutil.copy2(PCK_SRC,PCK_DST)
shutil.copy2(JS_SRC,JS_DST)
shutil.copy2(CLOUD_SRC,CLOUD_DST)

html_path=ROOT/"index.html"
html=html_path.read_text(encoding="utf-8")

# Keep the stable beta.19 shell/updater, but point it at versioned proven assets.
html=html.replace(
    '<script src="shared/afb-api.js"></script>\n\t\t<script src="index.js"></script>',
    '<script src="shared/afb-api.js"></script>\n\t\t<script src="shared/afb-cloud-accountsync1.js?v=0.7.9-beta.19-accountsync1"></script>\n\t\t<script src="index-accountsync1.js?v=0.7.9-beta.19-accountsync1"></script>',
    1,
)

pck_size=PCK_DST.stat().st_size
wasm_size=(ROOT/"index.wasm").stat().st_size
config_match=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
if not config_match:
    raise SystemExit("GODOT_CONFIG missing")
config=config_match.group(1)
config=re.sub(
    r'"fileSizes":\{[^}]*\}',
    f'"fileSizes":{{"index-accountsync1.pck":{pck_size},"index.wasm":{wasm_size}}}',
    config,
    count=1,
)
if '"mainPack"' in config:
    config=re.sub(r'"mainPack":"[^"]*"', '"mainPack":"index-accountsync1.pck"', config, count=1)
else:
    config=config.replace('"focusCanvas":true','"focusCanvas":true,"mainPack":"index-accountsync1.pck"',1)
config=re.sub(r'"serviceWorker":"[^"]*"','"serviceWorker":"index.service.worker.js"',config,count=1)
html=html[:config_match.start(1)]+config+html[config_match.end(1):]

html=html.replace(
    'let AFB_GAME_STARTED = false;',
    'let AFB_GAME_STARTED = false;\nlet AFB_GAME_STARTING = false;',
    1,
)

start=html.find("function afbLaunchGame() {")
end=html.find("function launchGodotEngine() {",start)
if start < 0 or end < 0:
    raise SystemExit("Launch function markers missing")
new_launch='''async function afbLaunchGame() {
\tif (AFB_GAME_STARTED || AFB_GAME_STARTING) return;
\tAFB_GAME_STARTING = true;
\ttry {
\t\tif (window.AFB_CLOUD && window.AFB_API && AFB_API.getPlayerSession && AFB_API.getPlayerSession()) {
\t\t\tawait AFB_CLOUD.reconcileLatestSilently();
\t\t}
\t} catch (error) {
\t\tconsole.warn('AFewBuds account career reconcile skipped; using local career.', error);
\t}
\tAFB_GAME_STARTED = true;
\tAFB_GAME_STARTING = false;
\tdocument.getElementById('afb-account-gate').hidden = true;
\tif (window.AFB_UPDATER) AFB_UPDATER.notifyGameStarting();
\tafbLoadTracker();
\tif (window.AFB_CLOUD) AFB_CLOUD.startAutoSync();
\tlaunchGodotEngine();
}
'''
html=html[:start]+new_launch+html[end:]

html=html.replace(
    'Sign in or create an account to track your play time and keep your AFewBuds identity. Email is optional and only used for updates when you opt in.',
    'Sign in or create an account to keep one AFewBuds career across your PC, phone browser, and Home Screen app. Email is optional and only used for updates when you opt in.',
    1,
)
html=html.replace(
    'Your existing browser career is not deleted by signing in, signing up, or continuing as a guest.',
    'One signed-in AFewBuds account uses one shared career across supported web devices. Guest play stays local to that device.',
    1,
)
html_path.write_text(html,encoding="utf-8")

(ROOT/"BUILD_VERSION.txt").write_text(
    f"AFewBuds game build: {GAME_BUILD}\nWeb release: {RELEASE_ID}\nUpdater protocol: 1\n",
    encoding="utf-8",
)
(ROOT/"RELEASE_NOTES_ACCOUNTSYNC1.txt").write_text(
    """AFewBuds 0.7.9-beta.19-accountsync1

- Keeps the known-good beta.19 game runtime baseline.
- One signed-in account uses one canonical career across PC browser, phone browser, and Home Screen/PWA.
- The newer account/device career is reconciled silently before Godot starts.
- Cloud restore is handed directly into Godot before _load_game(), fixing fresh iPhone Home Screen sessions starting a new career.
- Normal autosaves continue syncing silently in the background.
- Phone -> System adds Save Game and Save & Sleep / Quit.
- Manual save gives the player an explicit in-game save confirmation.
- Uses versioned JS/PCK asset names to avoid stale mixed-build PCK failures.
""",
    encoding="utf-8",
)

release_files=[
    "index.html",
    "index-accountsync1.js",
    "index-accountsync1.pck",
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
    "shared/afb-cloud-accountsync1.js",
    "shared/afb-updater.js",
    "shared/afb-tracker.js",
    "shared/style.css",
    "account/index.html",
    "admin/index.html",
]
manifest=[]
for name in release_files:
    p=ROOT/name
    if not p.exists():
        raise SystemExit(f"Manifest file missing: {name}")
    data=p.read_bytes()
    manifest.append({
        "path":name,
        "size":len(data),
        "sha256":hashlib.sha256(data).hexdigest(),
    })

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
        "safe-sleep-quit",
        "transactional-updater",
    ],
    "files":manifest,
}
(ROOT/"version.json").write_text(json.dumps(version,indent=2)+"\n",encoding="utf-8")

integrity={
    "release_id":RELEASE_ID,
    "game_build":GAME_BUILD,
    "index_html_sha256":next(x["sha256"] for x in manifest if x["path"]=="index.html"),
    "main_pack":"index-accountsync1.pck",
    "main_pack_size":pck_size,
    "main_pack_sha256":next(x["sha256"] for x in manifest if x["path"]=="index-accountsync1.pck"),
    "release_files":len(manifest),
}
(ROOT/"ACCOUNTSYNC1_INTEGRITY.json").write_text(json.dumps(integrity,indent=2)+"\n",encoding="utf-8")

print(json.dumps(integrity,indent=2))
