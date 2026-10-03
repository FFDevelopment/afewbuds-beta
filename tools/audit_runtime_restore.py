from pathlib import Path
import struct,re
P=Path("index-accountsync9.pck")
blob=P.read_bytes(); fb=struct.unpack_from("<Q",blob,24)[0]; do=struct.unpack_from("<Q",blob,32)[0]
count=struct.unpack_from("<I",blob,do)[0]; pos=do+4; text=None
for _ in range(count):
    plen=struct.unpack_from("<I",blob,pos)[0]; pos+=4
    raw=blob[pos:pos+plen]; pos+=plen
    name=raw.rstrip(b"\0").decode()
    off=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
    size=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
    pos+=16; flags=struct.unpack_from("<I",blob,pos)[0]; pos+=4
    if name=="scripts/main.gd":
        text=blob[fb+off:fb+off+size].decode(); break
for term in ["func _restore_runtime_state","func _capture_runtime_state","restored_runtime","customer_waiting =","visit_seconds"]:
    i=text.find(term)
    print("\n---",term,i,"---")
    if i>=0: print(text[max(0,i-1800):i+7000])
