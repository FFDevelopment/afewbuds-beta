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


print("\n===== STATION DIRECT CLICK =====")
for i,line in enumerate(lines):
    low=line.lower()
    if ("station" in low or "world" in low or "approach" in low or "contextual" in low or "vault" in low or "storage" in low or "workbench" in low or "grow_supply_shelf" in low) and (
        line.startswith("func ") or "set_meta" in line or "pressed.connect" in line or "current_view" in line or "world_pointer_target" in line or "contextual_button" in line
    ):
        print("\n--- line", i+1, "---")
        print("\n".join(lines[max(0,i-12):min(len(lines),i+34)]))


print("\n===== ROOM INTERACTION FUNCTIONS =====")
for i,line in enumerate(lines):
    if line.startswith("func _room_interaction_at") or line.startswith("func _activate_room_interaction") or line.startswith("func _go_to_view") or line.startswith("func _finish") and "view" in line.lower():
        print("\n--- line", i+1, "---")
        print("\n".join(lines[i:min(len(lines),i+100)]))


print("\n===== VIEWS AND STATION MESHES =====")
for i,line in enumerate(lines):
    low=line.lower()
    if (
        '"main_workbench"' in line or '"main_storage"' in line or '"main_door"' in line or
        '"grow_supply_shelf"' in line or '"grow_system"' in line or '"grow_room_utility"' in line or
        '"grow_room_tent"' in line or '"grow_room_tent2"' in line or '"grow_room_tent3"' in line or
        "Packing" in line or "Workbench" in line or "StorageVault" in line or "FrontDoor" in line or
        "SupplyShelf" in line or "Climate" in line or "SystemPanel" in line
    ):
        print("\n--- line", i+1, "---")
        print("\n".join(lines[max(0,i-8):min(len(lines),i+24)]))


print("\n===== INTERACTION MESH NAME CANDIDATES =====")
patterns = ["Bench","Packing","Workbench","Storage","Vault","FrontDoor","Door","Supply","Shelf","Climate","Panel","TentBody","ExpansionTent2Body","ExpansionTent3Body"]
seen=set()
for line in lines:
    if "_add_box(" in line or "_add_cylinder(" in line or ".name =" in line:
        if any(p in line for p in patterns):
            val=line.strip()
            if val not in seen:
                seen.add(val)
                print(val)


print("\n===== INVENTORY / LOCKER / SALES CONTEXT =====")
keys = ["locker","cash","products","bagged_inventory","storage","dealer","sale","bagging","_open_storage_panel","_open_bagging_panel","_open_customer_sale","dealer_sales"]
for i,line in enumerate(lines):
    low=line.lower()
    if any(k in low for k in keys) and (
        line.startswith("func ") or
        line.startswith("var ") or
        "pressed.connect" in line or
        "products[" in line or
        "bagged_inventory" in line or
        "cash " in line or
        "cash=" in line
    ):
        print("\n--- line", i+1, "---")
        print("\n".join(lines[max(0,i-10):min(len(lines),i+36)]))


print("\n===== TARGETED INVENTORY FUNCTIONS =====")
wanted = [
    "_open_customer_sale","_accept_customer","_complete_customer","_make_sale","_sell",
    "_process_dealer","_dealer","_run_dealer","_bag","_finish_bag","_store",
    "_save_game","_load_game","_save_state","_serialize","_deserialize","_build_ui"
]
starts=[i for i,l in enumerate(lines) if l.startswith("func ")]
for i in starts:
    name=lines[i].split("(",1)[0].replace("func ","")
    if any(name.startswith(w) for w in wanted):
        j=next((x for x in starts if x>i),len(lines))
        print("\n===== "+lines[i]+" =====")
        print("\n".join(lines[i:j]))


print("\n===== PERSONAL SALE STOCK FUNCTIONS =====")
needles = ["_available_amount","_open_customer_sale","_complete_sale","_accept_sale","_sell_to_customer","_finalize_sale","active_request","product[\"stock\"]"]
for i,line in enumerate(lines):
    if line.startswith("func ") and any(n in line for n in needles):
        j=next((x for x in starts if x>i),len(lines))
        print("\n===== "+line+" =====")
        print("\n".join(lines[i:j]))


print("\n===== AVAILABLE AMOUNT CALLERS =====")
for i,line in enumerate(lines):
    if "_available_amount(" in line:
        print(i+1, line)


print("\n===== SALE AVAILABILITY CONTEXT =====")
for target in [8847,8894,8947]:
    a=max(0,target-22); b=min(len(lines),target+36)
    print("\n--- around", target, "---")
    print("\n".join(lines[a:b]))


print("\n===== CUSTOMER REQUEST GENERATION =====")
for target in [8705,8720,8765,8794]:
    a=max(0,target-28); b=min(len(lines),target+32)
    print("\n--- around", target, "---")
    print("\n".join(lines[a:b]))


print("\n===== READY ORDER =====")
for i,line in enumerate(lines):
    if line.startswith("func _ready"):
        j=next((x for x in starts if x>i),len(lines))
        print("\n".join(lines[i:j]))
        break


print("\n===== BACKPACK LOCKER VERIFY =====")
checks = [
    'const PersonalInventory = preload("res://scripts/personal_inventory.gd")',
    'var personal_weed: Dictionary = {}',
    'var locker_weed: Dictionary = {}',
    'var locker_cash: int = 0',
    '"personal_weed": personal_weed',
    '"locker_weed": locker_weed',
    '"locker_cash": locker_cash',
    'func _player_available_amount(product_name: String) -> int:',
    'func _consume_player_sale_stock(product_name: String, qty: int) -> bool:',
    '"station_locker"',
    'personal_inventory.open_locker()'
]
for c in checks:
    print(c, "=>", c in text)
print("dealer still business stock direct =>", 'var available: int = int(product.get("stock", 0))' in text)
print("player sale helper calls =>", text.count("_player_available_amount("))


print("\n===== INVENTORY INITIALIZATION CONTEXT =====")
for term in [
    'const PersonalInventory = preload("res://scripts/personal_inventory.gd")',
    'personal_inventory = PersonalInventory.new()',
    'personal_inventory.setup(self)',
    '"station_locker"',
    'func _any_modal_open() -> bool:'
]:
    idx=text.find(term)
    print("\nTERM",term,"AT",idx)
    if idx >= 0:
        line_no=text[:idx].count("\n")
        print("\n".join(lines[max(0,line_no-10):min(len(lines),line_no+30)]))


print("\n===== HUD Z ORDER / RUNTIME RESTORE =====")
for i,line in enumerate(lines):
    low=line.lower()
    if (
        line.startswith("func _restore_runtime_state") or
        line.startswith("func _capture_runtime_state") or
        line.startswith("func _save_runtime") or
        "restored_runtime" in line or
        "current_view" in line and ("runtime" in low or "restore" in low) or
        "z_index" in line or
        "mouse_filter" in line and "hud" in low
    ):
        print("\n--- line",i+1,"---")
        print("\n".join(lines[max(0,i-14):min(len(lines),i+60)]))


print("\n===== PCK HELPER SCRIPT VERIFY =====")
blob,fb,do,entries = parse_pck(Path("cloud-test/index-accountsync10.pck"))
emap={e["name"]:e for e in entries}
for name in ["scripts/personal_inventory.gd","scripts/inventory_slot.gd"]:
    print("\nFILE",name,"present=",name in emap)
    if name in emap:
        body=emap[name]["content"].decode("utf-8","replace")
        print(body[:12000])

print("\n===== MAIN INVENTORY INIT EXACT =====")
for term in [
    'const PersonalInventory = preload("res://scripts/personal_inventory.gd")',
    'personal_inventory = PersonalInventory.new()',
    'personal_inventory.setup(self)',
    'func _safe_resume_view',
    'func _restore_runtime_state() -> void:'
]:
    idx=text.find(term)
    print("\nTERM",term,"AT",idx)
    if idx>=0:
        ln=text[:idx].count("\n")
        print("\n".join(lines[max(0,ln-8):min(len(lines),ln+36)]))
