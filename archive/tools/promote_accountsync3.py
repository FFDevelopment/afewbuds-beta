from pathlib import Path
import hashlib, json, re, shutil
from datetime import datetime, timezone

RELEASE_ID="0.7.9-beta.19-accountsync3"
GAME_BUILD="0.7.9-beta.19"
ROOT=Path(".")
PCK_SRC=ROOT/"cloud-test/index-system-restore4.pck"
JS_SRC=ROOT/"cloud-test/index.js"
CLOUD_SRC=ROOT/"cloud-test/shared/afb-cloud.js"

PCK_DST=ROOT/"index-accountsync3.pck"
JS_DST=ROOT/"index-accountsync3.js"
CLOUD_DST=ROOT/"shared/afb-cloud-accountsync3.js"

for p in (PCK_SRC, JS_SRC, CLOUD_SRC):
    if not p.exists():
        raise SystemExit(f"Missing validated asset: {p}")

shutil.copy2(PCK_SRC,PCK_DST)
shutil.copy2(JS_SRC,JS_DST)
shutil.copy2(CLOUD_SRC,CLOUD_DST)

html_path=ROOT/"index.html"
html=html_path.read_text(encoding="utf-8")

html=re.sub(
    r'<script src="shared/afb-cloud-accountsync\d+\.js\?v=[^"]+"></script>',
    '<script src="shared/afb-cloud-accountsync3.js?v=0.7.9-beta.19-accountsync3"></script>',
    html,
    count=1,
)
html=re.sub(
    r'<script src="index-accountsync\d+\.js\?v=[^"]+"></script>',
    '<script src="index-accountsync3.js?v=0.7.9-beta.19-accountsync3"></script>',
    html,
    count=1,
)

pck_size=PCK_DST.stat().st_size
wasm_size=(ROOT/"index.wasm").stat().st_size
m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
if not m:
    raise SystemExit("GODOT_CONFIG missing")
config=m.group(1)
config=re.sub(
    r'"fileSizes":\{[^}]*\}',
    f'"fileSizes":{{"index-accountsync3.pck":{pck_size},"index.wasm":{wasm_size}}}',
    config,
    count=1,
)
config=re.sub(r'"mainPack":"[^"]*"','"mainPack":"index-accountsync3.pck"',config,count=1)
config=re.sub(r'"serviceWorker":"[^"]*"','"serviceWorker":"index.service.worker.js"',config,count=1)
html=html[:m.start(1)]+config+html[m.end(1):]
html_path.write_text(html,encoding="utf-8")

(ROOT/"BUILD_VERSION.txt").write_text(
    f"AFewBuds game build: {GAME_BUILD}\nWeb release: {RELEASE_ID}\nUpdater protocol: 1\n",
    encoding="utf-8",
)

(ROOT/"RELEASE_NOTES_ACCOUNTSYNC3.txt").write_text(
"""AFewBuds 0.7.9-beta.19-accountsync3

- Keeps the proven account/cross-device sync behavior from accountsync1.
- Keeps the green GAME SAVED notification for Phone -> System -> Save Game and moves it higher so it stays visible above the phone UI.
- Save & Sleep / Quit also uses the same green save notification before the safe pause screen.
- Removes the extra regular status-text save confirmation; automatic local saves and background cloud sync remain silent.
- Uses a new versioned PCK/JS asset set to avoid stale mixed-build cache failures.
""",
encoding="utf-8",
)

release_files=[
    "index.html",
    "index-accountsync3.js",
    "index-accountsync3.pck",
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
    "shared/afb-cloud-accountsync3.js",
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
        "transactional-updater",
    ],
    "files":manifest,
}
(ROOT/"version.json").write_text(json.dumps(version,indent=2)+"\n",encoding="utf-8")

integrity={
    "release_id":RELEASE_ID,
    "game_build":GAME_BUILD,
    "main_pack":"index-accountsync3.pck",
    "main_pack_size":pck_size,
    "main_pack_sha256":next(x["sha256"] for x in manifest if x["path"]=="index-accountsync3.pck"),
    "release_files":len(manifest),
}
(ROOT/"ACCOUNTSYNC3_INTEGRITY.json").write_text(json.dumps(integrity,indent=2)+"\n",encoding="utf-8")
print(json.dumps(integrity,indent=2))
