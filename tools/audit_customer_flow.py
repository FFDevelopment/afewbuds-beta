from pathlib import Path
import struct, hashlib, re

PCK=Path("index-accountsync8.pck")
TARGET="scripts/main.gd"

def parse_pck(path):
    blob=path.read_bytes()
    fb=struct.unpack_from("<Q",blob,24)[0]
    do=struct.unpack_from("<Q",blob,32)[0]
    count=struct.unpack_from("<I",blob,do)[0]
    pos=do+4
    for _ in range(count):
        plen=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        raw=blob[pos:pos+plen]; pos+=plen
        name=raw.rstrip(b"\0").decode("utf-8")
        off=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        size=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        md5=blob[pos:pos+16]; pos+=16
        flags=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        content=blob[fb+off:fb+off+size]
        if name==TARGET:
            return content.decode("utf-8")
    raise SystemExit("main.gd not found")

text=parse_pck(PCK)
lines=text.splitlines()
patterns=[
    r"customer", r"visitor", r"business_open", r"lay_low", r"raid_lockdown",
    r"next_.*customer", r"spawn_.*customer", r"schedule_.*customer", r"queue_.*customer",
    r"customer_.*timer", r"door", r"away"
]
hits=[]
for i,line in enumerate(lines):
    low=line.lower()
    if any(re.search(p,low) for p in patterns):
        hits.append(i)

# Print contiguous function blocks that contain hits.
func_starts=[i for i,l in enumerate(lines) if l.startswith("func ")]
seen=set()
for h in hits:
    start=max([i for i in func_starts if i<=h], default=max(0,h-8))
    end=next((i for i in func_starts if i>start), min(len(lines),start+120))
    name=lines[start] if start < len(lines) else ""
    if start in seen: continue
    # limit to genuinely relevant customer/state functions
    block="\n".join(lines[start:end])
    if not any(k in block.lower() for k in ["customer","business_open","lay_low","raid_lockdown","visitor"]):
        continue
    seen.add(start)
    print("\n===== "+name+" =====")
    print(block[:12000])

print("\n===== KEY GLOBALS =====")
for i,l in enumerate(lines):
    if any(k in l for k in ["business_open", "lay_low_active", "raid_lockdown_until_day", "customer_timer", "next_customer", "customer_active", "current_customer"]):
        if l.startswith("var ") or l.startswith("const "):
            print(f"{i+1}: {l}")

print("\n===== DEBUG REEVES CHECK =====")
for needle in ["OS.is_debug_build() and not reeves_met","FORCE REEVES","Force Reeves"]:
    print(needle, needle in text)
