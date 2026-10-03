from pathlib import Path
import struct, hashlib, json, re, shutil
from datetime import datetime, timezone

RELEASE_ID="0.7.9-beta.19-accountsync10"
GAME_BUILD="0.7.9-beta.19"
ROOT=Path(".")
PCK_SRC=ROOT/"index-accountsync9.pck"
PCK_DST=ROOT/"index-accountsync10.pck"
JS_SRC=ROOT/"index-accountsync9.js"
JS_DST=ROOT/"index-accountsync10.js"
CLOUD_SRC=ROOT/"shared/afb-cloud-accountsync9.js"
CLOUD_DST=ROOT/"shared/afb-cloud-accountsync10.js"
TARGET="scripts/main.gd"

def align(n,a): return (n+a-1)//a*a
def parse(path):
    b=path.read_bytes(); fb=struct.unpack_from("<Q",b,24)[0]; do=struct.unpack_from("<Q",b,32)[0]
    count=struct.unpack_from("<I",b,do)[0]; pos=do+4; out=[]
    for _ in range(count):
        plen=struct.unpack_from("<I",b,pos)[0]; pos+=4
        raw=b[pos:pos+plen]; pos+=plen; name=raw.rstrip(b"\0").decode()
        off=struct.unpack_from("<Q",b,pos)[0]; pos+=8
        size=struct.unpack_from("<Q",b,pos)[0]; pos+=8
        md5=b[pos:pos+16]; pos+=16
        flags=struct.unpack_from("<I",b,pos)[0]; pos+=4
        c=b[fb+off:fb+off+size]
        if hashlib.md5(c).digest()!=md5: raise RuntimeError("MD5 mismatch: "+name)
        out.append((name,c,flags))
    return b,fb,out

def patch(text):
    marker='''\t_restore_timer_remaining(automation_timer, "automation_tick_seconds")
\t# A periodic timer's first restored interval must not change its normal cadence.
'''
    block='''\t_restore_timer_remaining(automation_timer, "automation_tick_seconds")

\t# Recover impossible/stale visitor sessions left by an interrupted sale or an
\t# older save. A customer that was answered but has no open sale and no active
\t# patience/exit timer must not permanently block all future visitors.
\tvar restored_sale_open: bool = bool(restored_runtime.get("sale_open", false))
\tvar restored_patience: float = float(restored_runtime.get("patience_seconds", -1.0))
\tvar restored_exit: float = float(restored_runtime.get("exit_seconds", -1.0))
\tvar stale_customer_session: bool = customer_waiting and customer_answered and not restored_sale_open and restored_patience <= 0.0 and restored_exit <= 0.0
\tif stale_customer_session:
\t\tcustomer_waiting = false
\t\tcustomer_departing = false
\t\tcustomer_answered = false
\t\tpeephole_checked = false
\t\tcurrent_customer = {}
\t\tactive_request = {}
\t\tknock_banner.visible = false
\t\tif customer_patience_timer != null:
\t\t\tcustomer_patience_timer.stop()
\t\tif customer_exit_timer != null:
\t\t\tcustomer_exit_timer.stop()

\t# A periodic timer's first restored interval must not change its normal cadence.
'''
    if marker not in text: raise RuntimeError("runtime timer marker not found")
    text=text.replace(marker,block,1)

    end_marker='''\telif bool(restored_runtime.get("phone_open", false)) and not daily_report_pending:
\t\tphone_open = true
\t\tphone_panel.visible = true
\t\tphone_current_app = str(restored_runtime.get("phone_app", "home"))

func _restore_timer_remaining(timer: Timer, key: String) -> void:
'''
    end_new='''\telif bool(restored_runtime.get("phone_open", false)) and not daily_report_pending:
\t\tphone_open = true
\t\tphone_panel.visible = true
\t\tphone_current_app = str(restored_runtime.get("phone_app", "home"))

\t# If the restored save has no active visitor and no restored visit timer,
\t# explicitly arm a new visit. _schedule_next_customer() still respects
\t# storefront closed/Lay Low, raid lockdown/simulation blocks, and listed stock.
\tif not customer_waiting and visit_timer != null and visit_timer.is_stopped() and not _simulation_blocked():
\t\t_schedule_next_customer(true)

func _restore_timer_remaining(timer: Timer, key: String) -> void:
'''
    if end_marker not in text: raise RuntimeError("runtime restore end marker not found")
    text=text.replace(end_marker,end_new,1)

    if "_schedule_next_customer(true)" not in text or "stale_customer_session" not in text:
        raise RuntimeError("stale customer recovery missing")
    if "OS.is_debug_build() and not reeves_met" in text or "FORCE REEVES" in text.upper():
        raise RuntimeError("Force Reeves debug unexpectedly present")
    return text

def rebuild():
    orig,fb,entries=parse(PCK_SRC); patched=[]; found=False
    for name,c,flags in entries:
        if name==TARGET:
            found=True; c=patch(c.decode()).encode()
        patched.append((name,c,flags))
    if not found: raise RuntimeError("main.gd not found")
    out=bytearray(orig[:fb]); cur=0; directory=[]
    for name,c,flags in patched:
        target=align(cur,32)
        if target>cur: out.extend(b"\0"*(target-cur))
        off=target; out.extend(c); cur=off+len(c)
        directory.append((name,off,len(c),hashlib.md5(c).digest(),flags))
    ndo=align(len(out),32)
    if ndo>len(out): out.extend(b"\0"*(ndo-len(out)))
    struct.pack_into("<Q",out,32,ndo); out.extend(struct.pack("<I",len(directory)))
    for name,off,size,md5,flags in directory:
        raw=name.encode(); plen=align(len(raw),4)
        out.extend(struct.pack("<I",plen)); out.extend(raw); out.extend(b"\0"*(plen-len(raw)))
        out.extend(struct.pack("<Q",off)); out.extend(struct.pack("<Q",size)); out.extend(md5); out.extend(struct.pack("<I",flags))
    PCK_DST.write_bytes(out)

rebuild(); shutil.copy2(JS_SRC,JS_DST); shutil.copy2(CLOUD_SRC,CLOUD_DST)
html_path=ROOT/"index.html"; html=html_path.read_text()
html=re.sub(r'<script src="shared/afb-cloud-accountsync\d+\.js\?v=[^"]+"></script>','<script src="shared/afb-cloud-accountsync10.js?v=0.7.9-beta.19-accountsync10"></script>',html,count=1)
html=re.sub(r'<script src="index-accountsync\d+\.js\?v=[^"]+"></script>','<script src="index-accountsync10.js?v=0.7.9-beta.19-accountsync10"></script>',html,count=1)
ps=PCK_DST.stat().st_size; ws=(ROOT/"index.wasm").stat().st_size
m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html); cfg=m.group(1)
cfg=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-accountsync10.pck":{ps},"index.wasm":{ws}}}',cfg,count=1)
cfg=re.sub(r'"mainPack":"[^"]*"','"mainPack":"index-accountsync10.pck"',cfg,count=1)
html=html[:m.start(1)]+cfg+html[m.end(1):]; html_path.write_text(html)

(ROOT/"BUILD_VERSION.txt").write_text(f"AFewBuds game build: {GAME_BUILD}\nWeb release: {RELEASE_ID}\nUpdater protocol: 1\n")
(ROOT/"RELEASE_NOTES_ACCOUNTSYNC10.txt").write_text("""AFewBuds 0.7.9-beta.19-accountsync10

- Keeps all validated accountsync9 behavior.
- Automatically detects and clears stale answered customer sessions restored without an active sale/patience/exit timer.
- Clears stale current customer/request state and explicitly re-arms the next customer timer after recovery.
- Also re-arms customer scheduling after load whenever no visitor and no visit timer are active.
- Existing storefront/Lay Low, raid lockdown, listed-stock, and simulation-block rules remain respected.
- Force Reeves debug remains removed.
""")
files=["index.html","index-accountsync10.js","index-accountsync10.pck","index.wasm","index.audio.worklet.js","index.audio.position.worklet.js","index.offline.html","index.icon.png","index.apple-touch-icon.png","index.png","index.manifest.json","index.144x144.png","index.180x180.png","index.192x192.png","index.512x512.png","index.service.worker.js","afewbuds-update.html","shared/config.js","shared/afb-api.js","shared/afb-cloud-accountsync10.js","shared/afb-updater.js","shared/afb-tracker.js","shared/style.css","account/index.html","admin/index.html"]
manifest=[]
for n in files:
    d=(ROOT/n).read_bytes(); manifest.append({"path":n,"size":len(d),"sha256":hashlib.sha256(d).hexdigest()})
version={"updater_protocol":1,"release_id":RELEASE_ID,"game_build":GAME_BUILD,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"web_features":["single-account-career","cross-device-cloud-sync","direct-godot-cloud-restore","silent-background-sync","phone-manual-save","manual-save-toast","safe-sleep-quit","portable-ui-glyphs","persistent-admin-session","claim-all-rewards","highlighted-phone-hud-button","reeves-8000-protection-balance","reeves-pay-half-full-refuse","lay-low-lights-down","heat-state-machine-fixes","persistent-enforcement-report","force-reeves-debug-removed","customer-traffic-fallback","stale-customer-runtime-recovery","transactional-updater"],"files":manifest}
(ROOT/"version.json").write_text(json.dumps(version,indent=2)+"\n")
integrity={"release_id":RELEASE_ID,"game_build":GAME_BUILD,"main_pack":"index-accountsync10.pck","main_pack_size":ps,"main_pack_sha256":next(x["sha256"] for x in manifest if x["path"]=="index-accountsync10.pck"),"release_files":len(manifest)}
(ROOT/"ACCOUNTSYNC10_INTEGRITY.json").write_text(json.dumps(integrity,indent=2)+"\n")
print(json.dumps(integrity,indent=2))
