from pathlib import Path
import struct,re
p=Path("index-accountsync10.pck")
b=p.read_bytes()
fb=struct.unpack_from("<Q",b,24)[0]
do=struct.unpack_from("<Q",b,32)[0]
count=struct.unpack_from("<I",b,do)[0]
pos=do+4
text=""
for _ in range(count):
    plen=struct.unpack_from("<I",b,pos)[0]; pos+=4
    raw=b[pos:pos+plen]; pos+=plen
    name=raw.rstrip(b"\0").decode()
    off=struct.unpack_from("<Q",b,pos)[0]; pos+=8
    size=struct.unpack_from("<Q",b,pos)[0]; pos+=8
    pos+=20
    if name=="scripts/main.gd":
        text=b[fb+off:fb+off+size].decode()
        break
lines=text.splitlines()
starts=[i for i,l in enumerate(lines) if l.startswith("func ")]
for i in starts:
    name=lines[i]
    if "peephole" in name.lower() or "customer_art" in name.lower() or "door_art" in name.lower():
        j=next((x for x in starts if x>i),len(lines))
        print("\n===== "+name+" =====")
        print("\n".join(lines[i:j]))
