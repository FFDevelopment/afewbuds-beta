from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, urllib.request

ROOT = Path(".")
RELEASE_ID = "0.7.9-beta.19-accountsync14"
GAME_BUILD = "0.7.9-beta.19"
CLOUD_REPO = "FFDevelopment/afewbuds-cloud-test"
CLOUD_COMMIT = "189fe53f4729a1680b2259f838e893a9ccb88853"
CLOUD_PATH = "index-cloudtest10.pck"
EXPECTED_GIT_BLOB = "6773451bf4c655ac15f87ea6df0a0333502d430c"
EXPECTED_SIZE = 25559140
RAW_URL = f"https://raw.githubusercontent.com/{CLOUD_REPO}/{CLOUD_COMMIT}/{CLOUD_PATH}"

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def download_exact_runtime() -> bytes:
    req = urllib.request.Request(RAW_URL, headers={"User-Agent": "AFewBuds-accountsync14-promoter"})
    with urllib.request.urlopen(req, timeout=180) as response:
        data = response.read()
    if len(data) != EXPECTED_SIZE:
        raise RuntimeError(f"cloudtest57 size mismatch: {len(data)} != {EXPECTED_SIZE}")
    actual_blob = git_blob_sha(data)
    if actual_blob != EXPECTED_GIT_BLOB:
        raise RuntimeError(f"cloudtest57 blob mismatch: {actual_blob} != {EXPECTED_GIT_BLOB}")
    return data

# Exact game runtime validated on iPhone in cloudtest.57.
pck = download_exact_runtime()
(ROOT / "index-accountsync14.pck").write_bytes(pck)

# No web/account behavior changed in this release. Version the existing wrappers so
# transactional updater clients fetch a complete, self-consistent release.
shutil.copy2(ROOT / "index-accountsync13.js", ROOT / "index-accountsync14.js")
shutil.copy2(ROOT / "shared/afb-cloud-accountsync13.js", ROOT / "shared/afb-cloud-accountsync14.js")

html_path = ROOT / "index.html"
html = html_path.read_text()

# Normalize either the current production accountsync13 shell or a previously
# prepared accountsync14 shell into the exact accountsync14 release shell.
if "shared/afb-cloud-accountsync13.js?v=0.7.9-beta.19-accountsync13" in html:
    html = html.replace(
        "shared/afb-cloud-accountsync13.js?v=0.7.9-beta.19-accountsync13",
        f"shared/afb-cloud-accountsync14.js?v={RELEASE_ID}",
        1,
    )
if "index-accountsync13.js?v=0.7.9-beta.19-accountsync13" in html:
    html = html.replace(
        "index-accountsync13.js?v=0.7.9-beta.19-accountsync13",
        f"index-accountsync14.js?v={RELEASE_ID}",
        1,
    )
if 'const AFB_TEST_RELEASE = "0.7.9-beta.19-accountsync13";' in html:
    html = html.replace(
        'const AFB_TEST_RELEASE = "0.7.9-beta.19-accountsync13";',
        f'const AFB_TEST_RELEASE = "{RELEASE_ID}";',
        1,
    )

html, size_count = re.subn(
    r'"fileSizes":\{"index-accountsync(?:13|14)\.pck":\d+,"index\.wasm":37902138\}',
    f'"fileSizes":{{"index-accountsync14.pck":{len(pck)},"index.wasm":37902138}}',
    html,
    count=1,
)
if size_count != 1:
    raise RuntimeError("could not normalize production PCK fileSizes entry")

if '"mainPack":"index-accountsync13.pck"' in html:
    html = html.replace(
        '"mainPack":"index-accountsync13.pck"',
        '"mainPack":"index-accountsync14.pck"',
        1,
    )

html_path.write_text(html)

(ROOT / "BUILD_VERSION.txt").write_text(
    f"AFewBuds game build: {GAME_BUILD}\n"
    f"Web release: {RELEASE_ID}\n"
    "Updater protocol: 1\n"
)

(ROOT / "RELEASE_NOTES_ACCOUNTSYNC14.txt").write_text(f"""AFewBuds {RELEASE_ID}

Validated planting seed-picker fix promoted from cloudtest.57.

- Exact game PCK from {CLOUD_REPO}@{CLOUD_COMMIT}.
- Empty pots now list every seed type currently owned instead of stopping after the first 3.
- The direct planting picker is scrollable on mobile for larger seed collections.
- Owned genetics not present in SEED_ORDER are appended automatically, so future/reward genetics remain plantable.
- Preserves all validated accountsync13 gameplay systems, cloud saves, account settings, password recovery, leaderboard, service worker and transactional updater behavior.
- accountsync13 remains available as the rollback release.
""")

old_manifest = json.loads((ROOT / "version.json").read_text())
paths = []
for item in old_manifest.get("files", []):
    path = item["path"]
    if path == "index-accountsync13.js":
        path = "index-accountsync14.js"
    elif path == "index-accountsync13.pck":
        path = "index-accountsync14.pck"
    elif path == "shared/afb-cloud-accountsync13.js":
        path = "shared/afb-cloud-accountsync14.js"
    paths.append(path)

for required in ["index.html", "index-accountsync14.js", "index-accountsync14.pck", "shared/afb-cloud-accountsync14.js"]:
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
for feature in [
    "dealer-storage",
    "dealer-storage-tier-progression",
    "dealer-storage-premium-cabinet",
    "dealer-storage-double-doors",
    "dealer-storage-pause-safe",
    "dealer-ten-percent-commission",
    "dealer-daily-customer-lock",
    "persistent-upgrade-family-cards",
    "bagging-bench-iii",
    "continuous-bagging-1-4g",
    "main-room-layout-refresh",
    "modern-black-kitchen",
    "front-facing-packing-scale",
    "hidden-stash-wall-fit",
    "all-owned-seeds-planting-picker",
    "mobile-scrollable-seed-picker",
    "future-genetics-planting-picker",
]:
    if feature not in features:
        features.append(feature)

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
    "main_pack": "index-accountsync14.pck",
    "main_pack_git_blob": git_blob_sha((ROOT / "index-accountsync14.pck").read_bytes()),
    "main_pack_size": (ROOT / "index-accountsync14.pck").stat().st_size,
    "main_pack_sha256": hashlib.sha256((ROOT / "index-accountsync14.pck").read_bytes()).hexdigest(),
    "previous_release": "0.7.9-beta.19-accountsync13",
    "rollback_pack": "index-accountsync13.pck",
    "updater_protocol": 1,
}
if integrity["main_pack_git_blob"] != EXPECTED_GIT_BLOB:
    raise RuntimeError("promoted PCK is not byte-identical to validated cloudtest57")
(ROOT / "ACCOUNTSYNC14_INTEGRITY.json").write_text(json.dumps(integrity, indent=2) + "\n")

# Final shell invariants.
final_html = html_path.read_text()
checks = [
    f'shared/afb-cloud-accountsync14.js?v={RELEASE_ID}',
    f'index-accountsync14.js?v={RELEASE_ID}',
    f'const AFB_TEST_RELEASE = "{RELEASE_ID}";',
    f'"fileSizes":{{"index-accountsync14.pck":{len(pck)},"index.wasm":37902138}}',
    '"mainPack":"index-accountsync14.pck"',
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
# workflow trigger: accountsync14 validated cloudtest57 promotion
