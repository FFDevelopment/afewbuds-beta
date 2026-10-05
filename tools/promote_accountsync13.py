from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, shutil, urllib.request

ROOT = Path(".")
RELEASE_ID = "0.7.9-beta.19-accountsync13"
GAME_BUILD = "0.7.9-beta.19"
CLOUD_REPO = "FFDevelopment/afewbuds-cloud-test"
CLOUD_COMMIT = "c34b7bffc51eaf048e1a46cb3d36d60ddad8e7ee"
CLOUD_PATH = "index-cloudtest10.pck"
EXPECTED_GIT_BLOB = "bdd1e2086f1c585385dd9b241734bc18923ef7b7"
EXPECTED_SIZE = 25557828
RAW_URL = f"https://raw.githubusercontent.com/{CLOUD_REPO}/{CLOUD_COMMIT}/{CLOUD_PATH}"

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def download_exact_runtime() -> bytes:
    req = urllib.request.Request(RAW_URL, headers={"User-Agent": "AFewBuds-accountsync13-promoter"})
    with urllib.request.urlopen(req, timeout=180) as response:
        data = response.read()
    if len(data) != EXPECTED_SIZE:
        raise RuntimeError(f"cloudtest56 size mismatch: {len(data)} != {EXPECTED_SIZE}")
    actual_blob = git_blob_sha(data)
    if actual_blob != EXPECTED_GIT_BLOB:
        raise RuntimeError(f"cloudtest56 blob mismatch: {actual_blob} != {EXPECTED_GIT_BLOB}")
    return data

# Exact game runtime validated on iPhone in cloudtest.56.
pck = download_exact_runtime()
(ROOT / "index-accountsync13.pck").write_bytes(pck)

# No web/account behavior changed in this release. Version the existing wrappers so
# transactional updater clients fetch a complete, self-consistent release.
shutil.copy2(ROOT / "index-accountsync12.js", ROOT / "index-accountsync13.js")
shutil.copy2(ROOT / "shared/afb-cloud-accountsync12.js", ROOT / "shared/afb-cloud-accountsync13.js")

html_path = ROOT / "index.html"
html = html_path.read_text()

# Normalize either the current production accountsync12 shell or a previously
# prepared accountsync13 shell into the exact accountsync13 release shell.
if "shared/afb-cloud-accountsync12.js?v=0.7.9-beta.19-accountsync12" in html:
    html = html.replace(
        "shared/afb-cloud-accountsync12.js?v=0.7.9-beta.19-accountsync12",
        f"shared/afb-cloud-accountsync13.js?v={RELEASE_ID}",
        1,
    )
if "index-accountsync12.js?v=0.7.9-beta.19-accountsync12" in html:
    html = html.replace(
        "index-accountsync12.js?v=0.7.9-beta.19-accountsync12",
        f"index-accountsync13.js?v={RELEASE_ID}",
        1,
    )
if 'const AFB_TEST_RELEASE = "0.7.9-beta.19-accountsync12";' in html:
    html = html.replace(
        'const AFB_TEST_RELEASE = "0.7.9-beta.19-accountsync12";',
        f'const AFB_TEST_RELEASE = "{RELEASE_ID}";',
        1,
    )

html, size_count = re.subn(
    r'"fileSizes":\{"index-accountsync(?:12|13)\.pck":\d+,"index\.wasm":37902138\}',
    f'"fileSizes":{{"index-accountsync13.pck":{len(pck)},"index.wasm":37902138}}',
    html,
    count=1,
)
if size_count != 1:
    raise RuntimeError("could not normalize production PCK fileSizes entry")

if '"mainPack":"index-accountsync12.pck"' in html:
    html = html.replace(
        '"mainPack":"index-accountsync12.pck"',
        '"mainPack":"index-accountsync13.pck"',
        1,
    )

html_path.write_text(html)

(ROOT / "BUILD_VERSION.txt").write_text(
    f"AFewBuds game build: {GAME_BUILD}\n"
    f"Web release: {RELEASE_ID}\n"
    "Updater protocol: 1\n"
)

(ROOT / "RELEASE_NOTES_ACCOUNTSYNC13.txt").write_text(f"""AFewBuds {RELEASE_ID}

Validated gameplay/content release promoted from cloudtest.56.

- Exact game PCK from {CLOUD_REPO}@{CLOUD_COMMIT}.
- Preserves the validated instant mobile tap / 12px movement-threshold scrolling behavior.
- Dealer Storage is a dedicated dealer-only stock system with 100g / 200g / 300g / 400g tiers.
- Dealer Storage III introduces the premium double-door cabinet; IV increases capacity only.
- Dealers use 10% commission, no daily wage, and cannot serve the same customer twice in one game day across the dealer team.
- Dealer Storage has compact per-strain +1/+5/MAX and -1/-5/ALL transfers.
- Expandable upgrade families remain visible and progress one tier at a time.
- Bagging Bench III adds the industrial workstation plus continuous randomized 1-4g manual bagging.
- Main-room presentation includes the relocated Dealer Storage, shifted packing bench/storage shelf, modern black kitchen, corrected packing scale, hidden-stash wall fit, and grow-room door-frame clearance.
- Account settings, cross-device cloud saves, password recovery, global leaderboard, service worker and transactional updater shell are preserved from accountsync12.
- accountsync12 remains available as the rollback release.
""")

old_manifest = json.loads((ROOT / "version.json").read_text())
paths = []
for item in old_manifest.get("files", []):
    path = item["path"]
    if path == "index-accountsync12.js":
        path = "index-accountsync13.js"
    elif path == "index-accountsync12.pck":
        path = "index-accountsync13.pck"
    elif path == "shared/afb-cloud-accountsync12.js":
        path = "shared/afb-cloud-accountsync13.js"
    paths.append(path)

for required in ["index.html", "index-accountsync13.js", "index-accountsync13.pck", "shared/afb-cloud-accountsync13.js"]:
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
    "main_pack": "index-accountsync13.pck",
    "main_pack_git_blob": git_blob_sha((ROOT / "index-accountsync13.pck").read_bytes()),
    "main_pack_size": (ROOT / "index-accountsync13.pck").stat().st_size,
    "main_pack_sha256": hashlib.sha256((ROOT / "index-accountsync13.pck").read_bytes()).hexdigest(),
    "previous_release": "0.7.9-beta.19-accountsync12",
    "rollback_pack": "index-accountsync12.pck",
    "updater_protocol": 1,
}
if integrity["main_pack_git_blob"] != EXPECTED_GIT_BLOB:
    raise RuntimeError("promoted PCK is not byte-identical to validated cloudtest56")
(ROOT / "ACCOUNTSYNC13_INTEGRITY.json").write_text(json.dumps(integrity, indent=2) + "\n")

# Final shell invariants.
final_html = html_path.read_text()
checks = [
    f'shared/afb-cloud-accountsync13.js?v={RELEASE_ID}',
    f'index-accountsync13.js?v={RELEASE_ID}',
    f'const AFB_TEST_RELEASE = "{RELEASE_ID}";',
    f'"fileSizes":{{"index-accountsync13.pck":{len(pck)},"index.wasm":37902138}}',
    '"mainPack":"index-accountsync13.pck"',
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
# workflow trigger: accountsync13 validated cloudtest56 promotion
