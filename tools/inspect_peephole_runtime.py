from pathlib import Path
import struct,re
p=Path("cloud-test/index-accountsync10.pck")
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
    if "peephole" in name.lower() or "customer_art" in name.lower() or "door_art" in name.lower() or "door_view" in name.lower():
        j=next((x for x in starts if x>i),len(lines))
        print("\n===== "+name+" =====")
        print("\n".join(lines[i:j]))

print("\n===== PEEPHOLE VAR CONTEXT =====")
for i,line in enumerate(lines):
    if "peephole_portrait" in line or "peephole_silhouette" in line:
        print("\n".join(lines[max(0,i-8):min(len(lines),i+14)]))


print("\n===== CLIENT ROWS =====")
for line in lines:
    if line.startswith("\t{\"name\":"):
        print(line)

print("\n===== BASIC BALANCE =====")
print("braces", text.count("{"), text.count("}"))
print("brackets", text.count("["), text.count("]"))
print("parens", text.count("("), text.count(")"))


print("\n===== SEED SHOP CONTEXT =====")
for i,line in enumerate(lines):
    if "seed_catalog[seed_name]" in line or "SEED_ORDER" in line or "Frozen Purple" in line:
        print("\n--- line", i+1, "---")
        print("\n".join(lines[max(0,i-12):min(len(lines),i+22)]))


print("\n===== TASK MARKERS =====")
for i,line in enumerate(lines):
    if '"OK"' in line or '"[ ]"' in line or "'OK'" in line or "'[ ]'" in line:
        print("\n--- line", i+1, "---")
        print("\n".join(lines[max(0,i-6):min(len(lines),i+10)]))


print("\n===== TENT / POT NAVIGATION =====")
for i,line in enumerate(lines):
    low=line.lower()
    if ("tent" in low or "pot" in low or "plant_slot" in low) and (
        line.startswith("func ") or
        "pressed.connect" in line or
        "current_view" in line or
        "slot_index" in line
    ):
        print("\n--- line", i+1, "---")
        print("\n".join(lines[max(0,i-10):min(len(lines),i+28)]))


print("\n===== DIRECT POT INPUT GATE =====")
for i,line in enumerate(lines):
    if "_open_direct_plant" in line or "plant_direct_panel.visible" in line or "_set_world_controls_visible" in line or "_handle" in line and "input" in line.lower():
        print("\n--- line", i+1, "---")
        print("\n".join(lines[max(0,i-18):min(len(lines),i+45)]))
