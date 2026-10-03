from pathlib import Path
import struct, hashlib, json, re, shutil
from datetime import datetime, timezone

RELEASE_ID="0.7.9-beta.19-accountsync9"
GAME_BUILD="0.7.9-beta.19"
ROOT=Path(".")
PCK_SRC=ROOT/"index-accountsync8.pck"
PCK_DST=ROOT/"index-accountsync9.pck"
JS_SRC=ROOT/"index-accountsync8.js"
JS_DST=ROOT/"index-accountsync9.js"
CLOUD_SRC=ROOT/"shared/afb-cloud-accountsync8.js"
CLOUD_DST=ROOT/"shared/afb-cloud-accountsync9.js"
TARGET="scripts/main.gd"

def align(n,a): return (n+a-1)//a*a

def parse_pck(path):
    blob=path.read_bytes()
    fb=struct.unpack_from("<Q",blob,24)[0]
    do=struct.unpack_from("<Q",blob,32)[0]
    count=struct.unpack_from("<I",blob,do)[0]
    pos=do+4
    entries=[]
    for _ in range(count):
        plen=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        raw=blob[pos:pos+plen]; pos+=plen
        name=raw.rstrip(b"\0").decode("utf-8")
        off=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        size=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        md5=blob[pos:pos+16]; pos+=16
        flags=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        content=blob[fb+off:fb+off+size]
        if hashlib.md5(content).digest()!=md5: raise RuntimeError("MD5 mismatch: "+name)
        entries.append((name,content,flags))
    return blob,fb,entries

def patch_main(text):
    pattern=r'func _viable_customers\(\) -> Array\[Dictionary\]:\n.*?(?=func _open_customer_sale\(\) -> void:\n)'
    m=re.search(pattern,text,flags=re.S)
    if not m: raise RuntimeError("_viable_customers block not found")
    block=m.group(0)
    old='''\treturn result\n\n'''
    if old not in block: raise RuntimeError("_viable_customers return marker missing")
    fallback='''\t# Never let a genuinely open/listed storefront go dead only because every\n\t# preference/flexibility roll missed. A fallback buyer can still require a\n\t# substitute, preserving customer preferences without starving foot traffic.\n\tif result.is_empty() and not listed_names.is_empty():\n\t\tvar fallback_customers: Array[Dictionary] = []\n\t\tfor fallback_customer: Dictionary in customers:\n\t\t\tvar fallback_name: String = str(fallback_customer.get("name", ""))\n\t\t\tif not _friend_staff_role(fallback_name).is_empty():\n\t\t\t\tcontinue\n\t\t\tif grower_level < int(fallback_customer.get("unlock_level", 1)):\n\t\t\t\tcontinue\n\t\t\tfallback_customers.append(fallback_customer)\n\t\tif not fallback_customers.is_empty():\n\t\t\tresult.append(fallback_customers[rng.randi_range(0, fallback_customers.size() - 1)])\n\treturn result\n\n'''
    block=block.replace(old,fallback,1)
    text=text[:m.start()]+block+text[m.end():]
    if "OS.is_debug_build() and not reeves_met" in text or "FORCE REEVES" in text.upper():
        raise RuntimeError("Force Reeves debug unexpectedly present")
    if "fallback_customers" not in text:
        raise RuntimeError("Customer fallback patch missing")
    return text

def rebuild():
    original,fb,entries=parse_pck(PCK_SRC)
    patched=[]; found=False
    for name,content,flags in entries:
        if name==TARGET:
            found=True
            content=patch_main(content.decode("utf-8")).encode("utf-8")
        patched.append((name,content,flags))
    if not found: raise RuntimeError("main.gd not found")
    out=bytearray(original[:fb]); current=0; directory=[]
    for name,content,flags in patched:
        target=align(current,32)
        if target>current: out.extend(b"\0"*(target-current))
        offset=target; out.extend(content); current=offset+len(content)
        directory.append((name,offset,len(content),hashlib.md5(content).digest(),flags))
    ndo=align(len(out),32)
    if ndo>len(out): out.extend(b"\0"*(ndo-len(out)))
    struct.pack_into("<Q",out,32,ndo)
    out.extend(struct.pack("<I",len(directory)))
    for name,off,size,md5,flags in directory:
        raw=name.encode("utf-8"); plen=align(len(raw),4)
        out.extend(struct.pack("<I",plen)); out.extend(raw); out.extend(b"\0"*(plen-len(raw)))
        out.extend(struct.pack("<Q",off)); out.extend(struct.pack("<Q",size)); out.extend(md5); out.extend(struct.pack("<I",flags))
    PCK_DST.write_bytes(out)

rebuild()
shutil.copy2(JS_SRC,JS_DST); shutil.copy2(CLOUD_SRC,CLOUD_DST)

html_path=ROOT/"index.html"; html=html_path.read_text(encoding="utf-8")
html=re.sub(r'<script src="shared/afb-cloud-accountsync\d+\.js\?v=[^"]+"></script>','<script src="shared/afb-cloud-accountsync9.js?v=0.7.9-beta.19-accountsync9"></script>',html,count=1)
html=re.sub(r'<script src="index-accountsync\d+\.js\?v=[^"]+"></script>','<script src="index-accountsync9.js?v=0.7.9-beta.19-accountsync9"></script>',html,count=1)
pck_size=PCK_DST.stat().st_size; wasm_size=(ROOT/"index.wasm").stat().st_size
m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
config=m.group(1)
config=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-accountsync9.pck":{pck_size},"index.wasm":{wasm_size}}}',config,count=1)
config=re.sub(r'"mainPack":"[^"]*"','"mainPack":"index-accountsync9.pck"',config,count=1)
html=html[:m.start(1)]+config+html[m.end(1):]
html_path.write_text(html,encoding="utf-8")

(ROOT/"BUILD_VERSION.txt").write_text(f"AFewBuds game build: {GAME_BUILD}\nWeb release: {RELEASE_ID}\nUpdater protocol: 1\n",encoding="utf-8")
(ROOT/"RELEASE_NOTES_ACCOUNTSYNC9.txt").write_text("""AFewBuds 0.7.9-beta.19-accountsync9

- Keeps all validated accountsync8 cloud/save/UI/Heat/Reeves behavior.
- Force Reeves debug remains removed from the main tester build.
- Fixes an edge case where an open storefront with valid listed stock could repeatedly produce no viable customer when preference/flexibility rolls all missed.
- When normal matching produces no visitor, one unlocked non-staff customer is now selected as fallback; normal substitute rules still apply.
- LAY LOW / storefront AWAY and raid lockdown still intentionally stop customer traffic.
""",encoding="utf-8")

release_files=["index.html","index-accountsync9.js","index-accountsync9.pck","index.wasm","index.audio.worklet.js","index.audio.position.worklet.js","index.offline.html","index.icon.png","index.apple-touch-icon.png","index.png","index.manifest.json","index.144x144.png","index.180x180.png","index.192x192.png","index.512x512.png","index.service.worker.js","afewbuds-update.html","shared/config.js","shared/afb-api.js","shared/afb-cloud-accountsync9.js","shared/afb-updater.js","shared/afb-tracker.js","shared/style.css","account/index.html","admin/index.html"]
manifest=[]
for name in release_files:
    data=(ROOT/name).read_bytes()
    manifest.append({"path":name,"size":len(data),"sha256":hashlib.sha256(data).hexdigest()})
version={"updater_protocol":1,"release_id":RELEASE_ID,"game_build":GAME_BUILD,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"web_features":["single-account-career","cross-device-cloud-sync","direct-godot-cloud-restore","silent-background-sync","phone-manual-save","manual-save-toast","safe-sleep-quit","portable-ui-glyphs","persistent-admin-session","claim-all-rewards","highlighted-phone-hud-button","reeves-8000-protection-balance","reeves-pay-half-full-refuse","lay-low-lights-down","heat-state-machine-fixes","persistent-enforcement-report","force-reeves-debug-removed","customer-traffic-fallback","transactional-updater"],"files":manifest}
(ROOT/"version.json").write_text(json.dumps(version,indent=2)+"\n",encoding="utf-8")
integrity={"release_id":RELEASE_ID,"game_build":GAME_BUILD,"main_pack":"index-accountsync9.pck","main_pack_size":pck_size,"main_pack_sha256":next(x["sha256"] for x in manifest if x["path"]=="index-accountsync9.pck"),"release_files":len(manifest)}
(ROOT/"ACCOUNTSYNC9_INTEGRITY.json").write_text(json.dumps(integrity,indent=2)+"\n",encoding="utf-8")
print(json.dumps(integrity,indent=2))
