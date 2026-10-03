from pathlib import Path
import struct, hashlib, json, re, shutil
from datetime import datetime, timezone

RELEASE_ID="0.7.9-beta.19-accountsync8"
GAME_BUILD="0.7.9-beta.19"
ROOT=Path(".")
PCK_SRC=ROOT/"index-accountsync7.pck"
PCK_DST=ROOT/"index-accountsync8.pck"
JS_SRC=ROOT/"index-accountsync7.js"
JS_DST=ROOT/"index-accountsync8.js"
CLOUD_SRC=ROOT/"shared/afb-cloud-accountsync7.js"
CLOUD_DST=ROOT/"shared/afb-cloud-accountsync8.js"
TARGET="scripts/main.gd"

def align(n,a):
    return (n+a-1)//a*a

def parse_pck(path):
    blob=path.read_bytes()
    if blob[:4]!=b"GDPC":
        raise RuntimeError("Not a Godot PCK")
    file_base=struct.unpack_from("<Q",blob,24)[0]
    dir_offset=struct.unpack_from("<Q",blob,32)[0]
    count=struct.unpack_from("<I",blob,dir_offset)[0]
    pos=dir_offset+4
    entries=[]
    for _ in range(count):
        plen=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        raw=blob[pos:pos+plen]; pos+=plen
        name=raw.rstrip(b"\0").decode("utf-8")
        offset=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        size=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        md5=blob[pos:pos+16]; pos+=16
        flags=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        content=blob[file_base+offset:file_base+offset+size]
        if hashlib.md5(content).digest()!=md5:
            raise RuntimeError("MD5 mismatch: "+name)
        entries.append((name,content,flags))
    return blob,file_base,entries

def strip_force_reeves(text):
    lines=text.splitlines(keepends=True)
    needle="\tif OS.is_debug_build() and not reeves_met:"
    idx=None
    for i,line in enumerate(lines):
        if line.rstrip("\r\n")==needle:
            idx=i
            break
    if idx is None:
        raise RuntimeError("Force Reeves debug UI block not found")
    j=idx+1
    while j<len(lines):
        line=lines[j]
        if line.strip()=="":
            j+=1
            continue
        if line.startswith("\t\t"):
            j+=1
            continue
        break
    removed="".join(lines[idx:j])
    text="".join(lines[:idx]+lines[j:])
    if "OS.is_debug_build() and not reeves_met" in text:
        raise RuntimeError("Force Reeves debug condition still present")
    if "FORCE REEVES" in text.upper():
        raise RuntimeError("Force Reeves label still present")
    print("Removed Reeves debug block:")
    print(removed[:1200])
    return text

def rebuild_pck():
    original,file_base,entries=parse_pck(PCK_SRC)
    patched=[]
    found=False
    for name,content,flags in entries:
        if name==TARGET:
            found=True
            content=strip_force_reeves(content.decode("utf-8")).encode("utf-8")
        patched.append((name,content,flags))
    if not found:
        raise RuntimeError("scripts/main.gd not found")

    out=bytearray(original[:file_base])
    current=0
    directory=[]
    for name,content,flags in patched:
        target=align(current,32)
        if target>current:
            out.extend(b"\0"*(target-current))
        offset=target
        out.extend(content)
        current=offset+len(content)
        directory.append((name,offset,len(content),hashlib.md5(content).digest(),flags))

    new_dir_offset=align(len(out),32)
    if new_dir_offset>len(out):
        out.extend(b"\0"*(new_dir_offset-len(out)))
    struct.pack_into("<Q",out,32,new_dir_offset)
    out.extend(struct.pack("<I",len(directory)))
    for name,offset,size,md5,flags in directory:
        raw=name.encode("utf-8")
        plen=align(len(raw),4)
        out.extend(struct.pack("<I",plen))
        out.extend(raw)
        out.extend(b"\0"*(plen-len(raw)))
        out.extend(struct.pack("<Q",offset))
        out.extend(struct.pack("<Q",size))
        out.extend(md5)
        out.extend(struct.pack("<I",flags))
    PCK_DST.write_bytes(out)

for p in (PCK_SRC,JS_SRC,CLOUD_SRC):
    if not p.exists():
        raise SystemExit("Missing validated asset: "+str(p))

rebuild_pck()
shutil.copy2(JS_SRC,JS_DST)
shutil.copy2(CLOUD_SRC,CLOUD_DST)

html_path=ROOT/"index.html"
html=html_path.read_text(encoding="utf-8")
html=re.sub(r'<script src="shared/afb-cloud-accountsync\d+\.js\?v=[^"]+"></script>',
            '<script src="shared/afb-cloud-accountsync8.js?v=0.7.9-beta.19-accountsync8"></script>',html,count=1)
html=re.sub(r'<script src="index-accountsync\d+\.js\?v=[^"]+"></script>',
            '<script src="index-accountsync8.js?v=0.7.9-beta.19-accountsync8"></script>',html,count=1)

pck_size=PCK_DST.stat().st_size
wasm_size=(ROOT/"index.wasm").stat().st_size
m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
if not m:
    raise SystemExit("GODOT_CONFIG missing")
config=m.group(1)
config=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-accountsync8.pck":{pck_size},"index.wasm":{wasm_size}}}',config,count=1)
config=re.sub(r'"mainPack":"[^"]*"','"mainPack":"index-accountsync8.pck"',config,count=1)
config=re.sub(r'"serviceWorker":"[^"]*"','"serviceWorker":"index.service.worker.js"',config,count=1)
html=html[:m.start(1)]+config+html[m.end(1):]
html_path.write_text(html,encoding="utf-8")

(ROOT/"BUILD_VERSION.txt").write_text(
    f"AFewBuds game build: {GAME_BUILD}\nWeb release: {RELEASE_ID}\nUpdater protocol: 1\n",
    encoding="utf-8",
)
(ROOT/"RELEASE_NOTES_ACCOUNTSYNC8.txt").write_text(
"""AFewBuds 0.7.9-beta.19-accountsync8

- Keeps all validated accountsync7 gameplay, Heat/Reeves, cloud save, UI, admin-session and Claim All behavior.
- Removes the Force Reeves debug control now that the natural Reeves flow has been validated.
- Does not include the experimental Malik 3D model or cloud-test genetics additions.
""",encoding="utf-8")

release_files=[
    "index.html","index-accountsync8.js","index-accountsync8.pck","index.wasm",
    "index.audio.worklet.js","index.audio.position.worklet.js","index.offline.html",
    "index.icon.png","index.apple-touch-icon.png","index.png","index.manifest.json",
    "index.144x144.png","index.180x180.png","index.192x192.png","index.512x512.png",
    "index.service.worker.js","afewbuds-update.html","shared/config.js","shared/afb-api.js",
    "shared/afb-cloud-accountsync8.js","shared/afb-updater.js","shared/afb-tracker.js",
    "shared/style.css","account/index.html","admin/index.html"
]
manifest=[]
for name in release_files:
    p=ROOT/name
    if not p.exists():
        raise SystemExit("Manifest file missing: "+name)
    data=p.read_bytes()
    manifest.append({"path":name,"size":len(data),"sha256":hashlib.sha256(data).hexdigest()})

version={
    "updater_protocol":1,
    "release_id":RELEASE_ID,
    "game_build":GAME_BUILD,
    "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    "web_features":[
        "single-account-career","cross-device-cloud-sync","direct-godot-cloud-restore",
        "silent-background-sync","phone-manual-save","manual-save-toast","safe-sleep-quit",
        "portable-ui-glyphs","persistent-admin-session","claim-all-rewards",
        "highlighted-phone-hud-button","reeves-8000-protection-balance",
        "reeves-pay-half-full-refuse","lay-low-lights-down","heat-state-machine-fixes",
        "persistent-enforcement-report","force-reeves-debug-removed","transactional-updater"
    ],
    "files":manifest,
}
(ROOT/"version.json").write_text(json.dumps(version,indent=2)+"\n",encoding="utf-8")
integrity={
    "release_id":RELEASE_ID,
    "game_build":GAME_BUILD,
    "main_pack":"index-accountsync8.pck",
    "main_pack_size":pck_size,
    "main_pack_sha256":next(x["sha256"] for x in manifest if x["path"]=="index-accountsync8.pck"),
    "release_files":len(manifest),
}
(ROOT/"ACCOUNTSYNC8_INTEGRITY.json").write_text(json.dumps(integrity,indent=2)+"\n",encoding="utf-8")
print(json.dumps(integrity,indent=2))
