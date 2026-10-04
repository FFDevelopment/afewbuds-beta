from pathlib import Path
import struct
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
    pos+=16+4
    if name=="scripts/main.gd":
        text=b[fb+off:fb+off+size].decode()
        break
for i,line in enumerate(text.splitlines()):
    if "peephole_art" in line or ('"name":' in line and "customers" not in line):
        if i<900:
            print(f"{i+1}: {line}")
