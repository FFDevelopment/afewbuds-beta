from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, urllib.request

ROOT = Path(".")
RELEASE_ID = "0.7.9-beta.19-accountsync12"
GAME_BUILD = "0.7.9-beta.19"
CLOUD_REPO = "FFDevelopment/afewbuds-cloud-test"
CLOUD_COMMIT = "ffdb0f7e9b7f57317a393c8d860bdf566d668a93"
CLOUD_PATH = "index-cloudtest10.pck"
EXPECTED_GIT_BLOB = "d9c8bee86e3d8b1d311144ac34d81b1bf7da4f8a"
EXPECTED_SIZE = 25538384
RAW_URL = f"https://raw.githubusercontent.com/{CLOUD_REPO}/{CLOUD_COMMIT}/{CLOUD_PATH}"

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def download_exact_runtime() -> bytes:
    req = urllib.request.Request(RAW_URL, headers={"User-Agent": "AFewBuds-accountsync12-promoter"})
    with urllib.request.urlopen(req, timeout=180) as response:
        data = response.read()
    if len(data) != EXPECTED_SIZE:
        raise RuntimeError(f"cloudtest41 size mismatch: {len(data)} != {EXPECTED_SIZE}")
    actual_blob = git_blob_sha(data)
    if actual_blob != EXPECTED_GIT_BLOB:
        raise RuntimeError(f"cloudtest41 blob mismatch: {actual_blob} != {EXPECTED_GIT_BLOB}")
    return data

# Exact game runtime validated on iPhone in cloudtest.41.
pck = download_exact_runtime()
(ROOT / "index-accountsync12.pck").write_bytes(pck)

# No web/account behavior changed in this release. Version the existing wrappers so
# transactional updater clients fetch a complete, self-consistent release.
shutil.copy2(ROOT / "index-accountsync11.js", ROOT / "index-accountsync12.js")
shutil.copy2(ROOT / "shared/afb-cloud-accountsync11.js", ROOT / "shared/afb-cloud-accountsync12.js")

html_path = ROOT / "index.html"
html = html_path.read_text()
required_old = [
    "shared/afb-cloud-accountsync11.js?v=0.7.9-beta.19-accountsync11",
    "index-accountsync11.js?v=0.7.9-beta.19-accountsync11",
    'const AFB_TEST_RELEASE = "0.7.9-beta.19-accountsync11";',
    '"index-accountsync11.pck":25541584',
    '"mainPack":"index-accountsync11.pck"',
]
for needle in required_old:
    if needle not in html:
        raise RuntimeError("accounts sync 11 HTML anchor missing: " + needle)

html = html.replace(
    "shared/afb-cloud-accountsync11.js?v=0.7.9-beta.19-accountsync11",
    f"shared/afb-cloud-accountsync12.js?v={RELEASE_ID}",
    1,
)
html = html.replace(
    "index-accountsync11.js?v=0.7.9-beta.19-accountsync11",
    f"index-accountsync12.js?v={RELEASE_ID}",
    1,
)
html = html.replace(
    'const AFB_TEST_RELEASE = "0.7.9-beta.19-accountsync11";',
    f'const AFB_TEST_RELEASE = "{RELEASE_ID}";',
    1,
)
html = html.replace(
    '"index-accountsync11.pck":25541584',
    f'"index-accountsync12.pck":{len(pck)}',
    1,
)
html = html.replace(
    '"mainPack":"index-accountsync11.pck"',
    '"mainPack":"index-accountsync12.pck"',
    1,
)
html_path.write_text(html)

(ROOT / "BUILD_VERSION.txt").write_text(
    f"AFewBuds game build: {GAME_BUILD}\n"
    f"Web release: {RELEASE_ID}\n"
    "Updater protocol: 1\n"
)

(ROOT / "RELEASE_NOTES_ACCOUNTSYNC12.txt").write_text(f"""AFewBuds {RELEASE_ID}

Validated mobile input hotfix promoted from cloudtest.41.

- Exact game PCK from {CLOUD_REPO}@{CLOUD_COMMIT}.
- Fixes iPhone/mobile phone categories requiring a long press.
- Stationary touch is a normal tap and opens immediately.
- Touch becomes scrolling only after 12px of actual movement.
- Swipe/scroll still cancels the underlying button action.
- Account settings, cloud saves, password recovery, leaderboard and updater behavior are unchanged.
- accountsync11 remains available as the transactional rollback release.
""")

old_manifest = json.loads((ROOT / "version.json").read_text())
paths = []
for item in old_manifest.get("files", []):
    path = item["path"]
    if path == "index-accountsync11.js":
        path = "index-accountsync12.js"
    elif path == "index-accountsync11.pck":
        path = "index-accountsync12.pck"
    elif path == "shared/afb-cloud-accountsync11.js":
        path = "shared/afb-cloud-accountsync12.js"
    paths.append(path)

for required in ["index.html", "index-accountsync12.js", "index-accountsync12.pck", "shared/afb-cloud-accountsync12.js"]:
    if required not in paths:
        raise RuntimeError("release manifest missing " + required)

manifest = []
for name in paths:
    data = (ROOT / name).read_bytes()
    manifest.append({
        "path": name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })

features = list(old_manifest.get("web_features", []))
if "instant-mobile-phone-taps" not in features:
    features.append("instant-mobile-phone-taps")
if "movement-threshold-phone-scroll" not in features:
    features.append("movement-threshold-phone-scroll")

version = {
    "updater_protocol": 1,
    "release_id": RELEASE_ID,
    "game_build": GAME_BUILD,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "web_features": features,
    "files": manifest,
}
(ROOT / "version.json").write_text(json.dumps(version, indent=2) + "\n")

integrity = {
    "release_id": RELEASE_ID,
    "game_build": GAME_BUILD,
    "source_cloud_repo": CLOUD_REPO,
    "source_cloud_commit": CLOUD_COMMIT,
    "source_cloud_path": CLOUD_PATH,
    "source_cloud_pck_blob": EXPECTED_GIT_BLOB,
    "main_pack": "index-accountsync12.pck",
    "main_pack_git_blob": git_blob_sha((ROOT / "index-accountsync12.pck").read_bytes()),
    "main_pack_size": (ROOT / "index-accountsync12.pck").stat().st_size,
    "main_pack_sha256": hashlib.sha256((ROOT / "index-accountsync12.pck").read_bytes()).hexdigest(),
    "previous_release": "0.7.9-beta.19-accountsync11",
    "rollback_pack": "index-accountsync11.pck",
    "updater_protocol": 1,
}
if integrity["main_pack_git_blob"] != EXPECTED_GIT_BLOB:
    raise RuntimeError("promoted PCK is not byte-identical to validated cloudtest41")
(ROOT / "ACCOUNTSYNC12_INTEGRITY.json").write_text(json.dumps(integrity, indent=2) + "\n")

# Final shell invariants.
final_html = html_path.read_text()
checks = [
    f'shared/afb-cloud-accountsync12.js?v={RELEASE_ID}',
    f'index-accountsync12.js?v={RELEASE_ID}',
    f'const AFB_TEST_RELEASE = "{RELEASE_ID}";',
    '"mainPack":"index-accountsync12.pck"',
    '"serviceWorker":"index.service.worker.js"',
    "AFB_UPDATER.notifyGameStarting()",
    "AFB_UPDATER.markGameReady()",
    'id="afb-leaderboard-modal"',
    'id="afb-account-settings-modal"',
]
for needle in checks:
    if needle not in final_html:
        raise RuntimeError("production shell invariant failed: " + needle)

print(json.dumps(integrity, indent=2))
