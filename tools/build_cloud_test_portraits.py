from pathlib import Path
import struct, hashlib, re, json

ROOT = Path(".")
BASE = ROOT / "index-accountsync10.pck"
OUT = ROOT / "cloud-test/index-accountsync10.pck"
ASSET_DIR = ROOT / "tools/peephole_clients96"
TARGET = "scripts/main.gd"

# Existing non-friend clients already in stable main. Their portrait filename is
# simply their lowercase name. The remaining images become new clients.
EXISTING_CLIENTS = [
    "Dre","Jules","Ashley","Maya","Nova","Rico","Skye","Knox","Avery",
    "Nia","CJ","Tasha","Eli","Sage","Kira","Zay","Bree",
]
NEW_CLIENTS = [
    {"name":"Ace","recognition_visits":2,"favorite":"Blue Frost","fallback_profile":"cool","flexibility":0.52,"min_qty":1,"max_qty":3,"tier":"Established","unlock_level":6},
    {"name":"Tino","recognition_visits":3,"favorite":"Solar Frost","fallback_profile":"solar","flexibility":0.30,"min_qty":3,"max_qty":6,"tier":"Reserve","unlock_level":14},
    {"name":"Carmen","recognition_visits":1,"favorite":"Street Green","fallback_profile":"balanced","flexibility":0.65,"min_qty":1,"max_qty":2,"tier":"New","unlock_level":2},
    {"name":"Marcus","recognition_visits":1,"favorite":"Purple Dream","fallback_profile":"balanced","flexibility":0.62,"min_qty":1,"max_qty":2,"tier":"New","unlock_level":3},
    {"name":"Simone","recognition_visits":2,"favorite":"Citrus Rush","fallback_profile":"citrus","flexibility":0.55,"min_qty":1,"max_qty":3,"tier":"Regular","unlock_level":4},
    {"name":"Dani","recognition_visits":2,"favorite":"Velvet Haze","fallback_profile":"smooth","flexibility":0.50,"min_qty":1,"max_qty":3,"tier":"Established","unlock_level":5},
    {"name":"Theo","recognition_visits":2,"favorite":"Golden Ember","fallback_profile":"gold","flexibility":0.45,"min_qty":2,"max_qty":4,"tier":"Established","unlock_level":7},
    {"name":"Devon","recognition_visits":2,"favorite":"Cherry Glow","fallback_profile":"cherry","flexibility":0.48,"min_qty":2,"max_qty":4,"tier":"Established","unlock_level":8},
    {"name":"Omar","recognition_visits":3,"favorite":"Neon Berry","fallback_profile":"berry","flexibility":0.40,"min_qty":2,"max_qty":5,"tier":"Established","unlock_level":9},
    {"name":"Nico","recognition_visits":3,"favorite":"Moon Cake","fallback_profile":"dessert","flexibility":0.36,"min_qty":3,"max_qty":5,"tier":"Premium","unlock_level":11},
    {"name":"Nolan","recognition_visits":3,"favorite":"Midnight Crown","fallback_profile":"luxury","flexibility":0.32,"min_qty":3,"max_qty":6,"tier":"Premium","unlock_level":12},
]
# Source portrait filenames from the user's selected 28. Nolan uses the spare
# image that was previously named tyler.webp; Friend Tyler remains untouched.
PORTRAIT_SOURCE = {
    "Dre":"dre.webp","Jules":"jules.webp","Ashley":"ashley.webp","Maya":"maya.webp",
    "Nova":"nova.webp","Rico":"rico.webp","Skye":"skye.webp","Knox":"knox.webp",
    "Avery":"avery.webp","Nia":"nia.webp","CJ":"cj.webp","Tasha":"tasha.webp",
    "Eli":"eli.webp","Sage":"sage.webp","Kira":"kira.webp","Zay":"zay.webp",
    "Bree":"bree.webp","Ace":"ace.webp","Tino":"tino.webp","Carmen":"carmen.webp",
    "Marcus":"marcus.webp","Simone":"simone.webp","Dani":"dani.webp","Theo":"theo.webp",
    "Devon":"devon.webp","Omar":"omar.webp","Nico":"nico.webp","Nolan":"tyler.webp",
}

GENETICS_TASKS = '''\t{"id": "recipe_citrus_velvet", "category": "Genetics", "tier": 2, "title": "Flavor Notes", "description": "Complete a hybrid batch and build a five-variety seed shelf.", "metric": "hybrids_created", "target": 1, "reward_cash": 0, "reward_xp": 90, "reward_rep": 5, "reward_recipe": "Citrus Velvet", "requires": [{"state": "seed_varieties", "target": 5, "label": "Seed varieties"}]},
\t{"id": "recipe_cherry_frost", "category": "Genetics", "tier": 3, "title": "Cold & Sweet", "description": "Create 3 hybrid batches and reach Grower Level 7.", "metric": "hybrids_created", "target": 3, "reward_cash": 0, "reward_xp": 150, "reward_rep": 8, "reward_recipe": "Cherry Frost", "requires": [{"state": "grower_level", "target": 7, "label": "Grower Level"}]},
\t{"id": "recipe_ember_berry", "category": "Genetics", "tier": 3, "title": "Color Theory", "description": "Create 5 hybrid batches and reach Grower Level 9.", "metric": "hybrids_created", "target": 5, "reward_cash": 0, "reward_xp": 200, "reward_rep": 10, "reward_recipe": "Ember Berry", "requires": [{"state": "grower_level", "target": 9, "label": "Grower Level"}]},
\t{"id": "recipe_crown_cake", "category": "Genetics", "tier": 4, "title": "Crown Lab", "description": "Create 8 hybrid batches, reach Grower Level 11, and complete 50 harvests.", "metric": "hybrids_created", "target": 8, "reward_cash": 0, "reward_xp": 300, "reward_rep": 15, "reward_recipe": "Crown Cake", "requires": [{"state": "grower_level", "target": 11, "label": "Grower Level"}, {"metric": "harvests", "target": 50, "label": "Harvests"}]},
'''

def align(n,a):
    return (n+a-1)//a*a

def parse_pck(path):
    blob=path.read_bytes()
    if blob[:4] != b"GDPC":
        raise RuntimeError("Not a Godot PCK")
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
        if hashlib.md5(content).digest()!=md5:
            raise RuntimeError("MD5 mismatch "+name)
        entries.append({"name":name,"off":off,"size":size,"md5":md5,"flags":flags,"content":content})
    return blob,fb,do,entries

def row(data):
    parts=[]
    for k,v in data.items():
        if isinstance(v,str):
            parts.append(json.dumps(k)+": "+json.dumps(v))
        elif isinstance(v,bool):
            parts.append(json.dumps(k)+": "+("true" if v else "false"))
        else:
            parts.append(json.dumps(k)+": "+str(v))
    return "\t{" + ", ".join(parts) + "},"

def add_new_clients(text):
    # Add after Bree, the last stable non-friend customer. Do not modify Friend
    # Tyler or any other Friend portrait/art fields.
    anchor_matches=list(re.finditer(r'^\t\{"name": "Bree".*?\},?$',text,re.M))
    if not anchor_matches:
        raise RuntimeError("Bree client anchor missing")
    pos=anchor_matches[-1].end()
    rows=[]
    for c in NEW_CLIENTS:
        if re.search(r'^\t\{"name": "'+re.escape(c["name"])+r'"',text,re.M):
            continue
        rows.append(row(c))
    if rows:
        text=text[:pos]+"\n"+"\n".join(rows)+text[pos:]
    return text

def patch_peephole(text):
    # Non-friend clients use assets/characters/peephole/<lowercase name>.webp.
    # Friends retain their original imported PNG portrait paths.
    old='''\tvar avatar_path: String = str(current_customer.get("peephole_art", current_customer.get("avatar", "")))
\tif not avatar_path.is_empty() and ResourceLoader.exists(avatar_path):
\t\tvar avatar_resource: Resource = load(avatar_path)
\t\tvar avatar_texture: Texture2D = avatar_resource as Texture2D
\t\tif avatar_texture != null and peephole_portrait != null:
\t\t\tpeephole_portrait.texture = avatar_texture
\t\t\tpeephole_portrait.visible = true
\t\t\tif peephole_silhouette != null:
\t\t\t\tpeephole_silhouette.visible = false
'''
    new='''\tvar avatar_path: String = str(current_customer.get("peephole_art", current_customer.get("avatar", "")))
\tif str(current_customer.get("tier", "")) != "Friend":
\t\tvar client_name: String = str(current_customer.get("name", "")).to_lower()
\t\tvar client_art: String = "res://assets/characters/peephole/%s.webp" % client_name
\t\tif FileAccess.file_exists(client_art):
\t\t\tavatar_path = client_art
\tvar avatar_texture: Texture2D = _load_peephole_texture(avatar_path)
\tif avatar_texture != null and peephole_portrait != null:
\t\tpeephole_portrait.texture = avatar_texture
\t\tpeephole_portrait.visible = true
\t\tif peephole_silhouette != null:
\t\t\tpeephole_silhouette.visible = false
'''
    if old not in text:
        # Accept a previous generated loader block by replacing only the function
        # body between avatar_path and the Reeves branch.
        pat=r'\tvar avatar_path: String = str\(current_customer\.get\("peephole_art".*?(?=\n\tif str\(current_customer\.get\("special", ""\)\) == "reeves":)'
        text,n=re.subn(pat,new.rstrip("\n"),text,count=1,flags=re.S)
        if n!=1:
            raise RuntimeError("Stable peephole avatar block not found")
    else:
        text=text.replace(old,new,1)

    loader='''func _load_peephole_texture(path: String) -> Texture2D:
\tif path.is_empty():
\t\treturn null
\tvar lower_path: String = path.to_lower()
\tif FileAccess.file_exists(path) and lower_path.ends_with(".webp"):
\t\tvar bytes: PackedByteArray = FileAccess.get_file_as_bytes(path)
\t\tvar image: Image = Image.new()
\t\tif image.load_webp_from_buffer(bytes) == OK:
\t\t\treturn ImageTexture.create_from_image(image)
\tif ResourceLoader.exists(path):
\t\treturn load(path) as Texture2D
\treturn null

'''
    marker='func _open_peephole() -> void:\n'
    pat=r'func _load_peephole_texture\(path: String\) -> Texture2D:\n.*?(?=func _open_peephole\(\) -> void:\n)'
    if re.search(pat,text,flags=re.S):
        text=re.sub(pat,loader,text,count=1,flags=re.S)
    else:
        if marker not in text:
            raise RuntimeError("Peephole function marker missing")
        text=text.replace(marker,loader+marker,1)
    return text



def patch_full_genetics(text):
    old_order='const SEED_ORDER: Array[String] = ["Street Green", "Purple Dream", "Citrus Rush", "Blue Frost", "Velvet Haze", "Frozen Purple", "Golden Ember", "Cherry Glow", "Neon Berry", "Moon Cake", "Midnight Crown", "Black Cherry", "Aurora Reserve", "Solar Frost"]'
    new_order='const SEED_ORDER: Array[String] = ["Street Green", "Purple Dream", "Citrus Rush", "Blue Frost", "Velvet Haze", "Frozen Purple", "Golden Ember", "Cherry Glow", "Neon Berry", "Moon Cake", "Midnight Crown", "Black Cherry", "Aurora Reserve", "Solar Frost", "Citrus Velvet", "Cherry Frost", "Ember Berry", "Crown Cake"]'
    if old_order not in text:
        raise RuntimeError("seed order marker missing")
    text=text.replace(old_order,new_order,1)

    inv_old='''\t"Aurora Reserve": 0
}'''
    inv_new='''\t"Aurora Reserve": 0,
\t"Citrus Velvet": 0,
\t"Cherry Frost": 0,
\t"Ember Berry": 0,
\t"Crown Cake": 0
}'''
    if inv_old not in text:
        raise RuntimeError("seed inventory marker missing")
    text=text.replace(inv_old,inv_new,1)

    cat_old='''\t"Solar Frost": {"unlock": 14, "cost": 210, "price": 70, "grade": "S+", "profile": "solar", "harvest": 5, "description": "Late-career prestige genetics intended for reserve-level customers."}
}'''
    cat_new='''\t"Solar Frost": {"unlock": 14, "cost": 210, "price": 70, "grade": "S+", "profile": "solar", "harvest": 5, "description": "Late-career prestige genetics intended for reserve-level customers."},
\t"Citrus Velvet": {"unlock": 99, "cost": 0, "price": 34, "grade": "S", "profile": "citrus", "harvest": 8, "recipe_only": true, "description": "A fictional crossbreed unlocked through Story rewards."},
\t"Cherry Frost": {"unlock": 99, "cost": 0, "price": 46, "grade": "S+", "profile": "cherry", "harvest": 6, "recipe_only": true, "description": "A fictional cold-fruit crossbreed unlocked through progression."},
\t"Ember Berry": {"unlock": 99, "cost": 0, "price": 54, "grade": "S+", "profile": "berry", "harvest": 6, "recipe_only": true, "description": "A fictional gold-and-berry crossbreed unlocked through progression."},
\t"Crown Cake": {"unlock": 99, "cost": 0, "price": 63, "grade": "S+", "profile": "luxury", "harvest": 5, "recipe_only": true, "description": "A fictional prestige crossbreed reserved for late-career genetics work."}
}'''
    if cat_old not in text:
        raise RuntimeError("seed catalog marker missing")
    text=text.replace(cat_old,cat_new,1)

    # Frozen Purple is also recipe-only now.
    frozen_pat=r'(\t"Frozen Purple": \{[^\n}]*)(\})'
    m=re.search(frozen_pat,text)
    if not m:
        raise RuntimeError("Frozen Purple catalog entry missing")
    frozen_line=m.group(0)
    if '"recipe_only": true' not in frozen_line:
        frozen_line=frozen_line[:-1]+', "recipe_only": true}'
        text=text[:m.start()]+frozen_line+text[m.end():]

    adv='''\t{"id": "three_hybrids", "category": "Genetics", "tier": 4, "title": "Breeding Program", "description": "Create 3 hybrid seed batches.", "metric": "hybrids_created", "target": 3, "reward_cash": 100, "reward_xp": 250, "reward_rep": 15},
'''
    if adv not in text:
        raise RuntimeError("genetics advancement marker missing")
    text=text.replace(adv,adv+GENETICS_TASKS,1)

    reward_vars='''\tvar reward_seed: String = str(entry.get("reward_seed", ""))
\tvar reward_seed_count: int = int(entry.get("reward_seed_count", 0))
'''
    if reward_vars not in text:
        raise RuntimeError("reward text vars missing")
    text=text.replace(reward_vars,reward_vars+'\tvar reward_recipe: String = str(entry.get("reward_recipe", ""))\n',1)

    reward_func_pat=r'func _advancement_reward_text\(entry: Dictionary\) -> String:\n.*?(?=\nfunc )'
    reward_match=re.search(reward_func_pat,text,flags=re.S)
    if not reward_match:
        raise RuntimeError("advancement reward function missing")
    reward_block=reward_match.group(0)
    if "GENETICS RECIPE:" not in reward_block:
        return_match=re.search(r'\n\treturn "[^"]*"\.join\(parts\)',reward_block)
        if not return_match:
            raise RuntimeError("advancement reward return missing")
        recipe_lines='\n\tif not reward_recipe.is_empty():\n\t\tparts.append("GENETICS RECIPE: %s" % reward_recipe)'
        reward_block=reward_block[:return_match.start()]+recipe_lines+reward_block[return_match.start():]
        text=text[:reward_match.start()]+reward_block+text[reward_match.end():]

    # Hide every recipe-only seed from Shop > Seeds.
    shop_anchor='next_unlock.text = "NEXT GENETIC'
    anchor=text.find(shop_anchor)
    if anchor < 0:
        raise RuntimeError("seed shop anchor missing")
    loop='''\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
'''
    loop_new='''\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif bool(info.get("recipe_only", false)):
\t\t\tcontinue
'''
    pos=text.find(loop,anchor)
    if pos < 0:
        raise RuntimeError("seed shop loop missing")
    text=text[:pos]+text[pos:].replace(loop,loop_new,1)

    next_old='''func _next_locked_seed_name() -> String:
\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif grower_level < int(info.get("unlock", 1)):
\t\t\treturn seed_name
\treturn ""
'''
    next_new='''func _next_locked_seed_name() -> String:
\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif bool(info.get("recipe_only", false)):
\t\t\tcontinue
\t\tif grower_level < int(info.get("unlock", 1)):
\t\t\treturn seed_name
\treturn ""
'''
    if next_old not in text:
        raise RuntimeError("next locked seed function missing")
    text=text.replace(next_old,next_new,1)

    # Defensive purchase block for every recipe-only hybrid.
    buy_old='''func _buy_seed(seed_name: String) -> void:
\tif tutorial_active:
'''
    buy_new='''func _buy_seed(seed_name: String) -> void:
\tif seed_catalog.has(seed_name):
\t\tvar purchase_info: Dictionary = seed_catalog[seed_name]
\t\tif bool(purchase_info.get("recipe_only", false)):
\t\t\tstatus_label.text = "%s is genetics-only. Create it in Phone -> Genetics." % seed_name
\t\t\treturn
\tif tutorial_active:
'''
    if buy_old not in text:
        raise RuntimeError("seed purchase function missing")
    text=text.replace(buy_old,buy_new,1)

    # Do not announce recipe-only strains as shop unlocks on level-up.
    level_old='''\t\tfor seed_name in SEED_ORDER:
\t\t\tif seed_catalog.has(seed_name):
\t\t\t\tvar seed_info: Dictionary = seed_catalog[seed_name]
\t\t\t\tif int(seed_info.get("unlock", 1)) == grower_level:
\t\t\t\t\tunlocked_names.append(seed_name)
'''
    level_new='''\t\tfor seed_name in SEED_ORDER:
\t\t\tif seed_catalog.has(seed_name):
\t\t\t\tvar seed_info: Dictionary = seed_catalog[seed_name]
\t\t\t\tif bool(seed_info.get("recipe_only", false)):
\t\t\t\t\tcontinue
\t\t\t\tif int(seed_info.get("unlock", 1)) == grower_level:
\t\t\t\t\tunlocked_names.append(seed_name)
'''
    if level_old not in text:
        raise RuntimeError("grower unlock loop missing")
    text=text.replace(level_old,level_new,1)

    genetics_new='''func _genetics_recipe_catalog() -> Array[Dictionary]:
\treturn [
\t\t{"id": "frozen_purple", "title": "FROZEN PURPLE", "parent_a": "Purple Dream", "parent_b": "Blue Frost", "output": "Frozen Purple", "count": 2, "min_level": 5, "unlock_task": "", "unlock_label": "Grower Level 5"},
\t\t{"id": "citrus_velvet", "title": "CITRUS VELVET", "parent_a": "Citrus Rush", "parent_b": "Velvet Haze", "output": "Citrus Velvet", "count": 2, "min_level": 5, "unlock_task": "recipe_citrus_velvet", "unlock_label": "Flavor Notes reward"},
\t\t{"id": "cherry_frost", "title": "CHERRY FROST", "parent_a": "Cherry Glow", "parent_b": "Blue Frost", "output": "Cherry Frost", "count": 2, "min_level": 7, "unlock_task": "recipe_cherry_frost", "unlock_label": "Cold & Sweet reward"},
\t\t{"id": "ember_berry", "title": "EMBER BERRY", "parent_a": "Golden Ember", "parent_b": "Neon Berry", "output": "Ember Berry", "count": 2, "min_level": 9, "unlock_task": "recipe_ember_berry", "unlock_label": "Color Theory reward"},
\t\t{"id": "crown_cake", "title": "CROWN CAKE", "parent_a": "Midnight Crown", "parent_b": "Moon Cake", "output": "Crown Cake", "count": 2, "min_level": 11, "unlock_task": "recipe_crown_cake", "unlock_label": "Crown Lab reward"}
\t]

func _genetics_recipe_unlocked(recipe: Dictionary) -> bool:
\tvar unlock_task: String = str(recipe.get("unlock_task", ""))
\treturn unlock_task.is_empty() or bool(advancement_claimed.get(unlock_task, false))

func _build_genetics_app() -> void:
\tvar intro: Label = Label.new()
\tintro.text = "GENETICS LAB - combine two parent seeds to create fictional hybrid seeds. Reward recipes unlock here after you claim the matching Story / Rewards task; they are never sold in Shop > Seeds."
\tintro.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\tphone_list.add_child(intro)
\tfor recipe: Dictionary in _genetics_recipe_catalog():
\t\tvar parent_a: String = str(recipe.get("parent_a", ""))
\t\tvar parent_b: String = str(recipe.get("parent_b", ""))
\t\tvar output_name: String = str(recipe.get("output", ""))
\t\tvar min_level: int = int(recipe.get("min_level", 1))
\t\tvar unlocked: bool = _genetics_recipe_unlocked(recipe)
\t\tvar a_owned: int = int(seed_inventory.get(parent_a, 0))
\t\tvar b_owned: int = int(seed_inventory.get(parent_b, 0))
\t\tvar card: PanelContainer = PanelContainer.new()
\t\tcard.add_theme_stylebox_override("panel", _style_box(Color("171d1a"), Color("496b55") if unlocked else Color("3e4541"), 14, 1))
\t\tphone_list.add_child(card)
\t\tvar box: VBoxContainer = VBoxContainer.new()
\t\tbox.add_theme_constant_override("separation", 7)
\t\tcard.add_child(box)
\t\tvar title: Label = Label.new()
\t\ttitle.text = str(recipe.get("title", output_name))
\t\ttitle.add_theme_font_size_override("font_size", 20)
\t\tbox.add_child(title)
\t\tvar detail: Label = Label.new()
\t\tdetail.text = "%s + %s\\nOwned: %s %d | %s %d\\nProduces: %dx %s seed" % [parent_a, parent_b, parent_a, a_owned, parent_b, b_owned, int(recipe.get("count", 2)), output_name]
\t\tdetail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\tbox.add_child(detail)
\t\tvar action: Button = Button.new()
\t\taction.custom_minimum_size.y = 50
\t\tif not unlocked:
\t\t\taction.text = "LOCKED - CLAIM %s" % str(recipe.get("unlock_label", "STORY REWARD")).to_upper()
\t\t\taction.disabled = true
\t\telif grower_level < min_level:
\t\t\taction.text = "REQUIRES GROWER LEVEL %d" % min_level
\t\t\taction.disabled = true
\t\telif a_owned < 1 or b_owned < 1:
\t\t\taction.text = "NEED BOTH PARENT SEEDS"
\t\t\taction.disabled = true
\t\telse:
\t\t\taction.text = "CREATE %s" % output_name.to_upper()
\t\t\taction.pressed.connect(_create_genetics_cross.bind(str(recipe.get("id", ""))))
\t\tbox.add_child(action)

func _create_genetics_cross(recipe_id: String) -> void:
\tvar selected: Dictionary = {}
\tfor recipe: Dictionary in _genetics_recipe_catalog():
\t\tif str(recipe.get("id", "")) == recipe_id:
\t\t\tselected = recipe
\t\t\tbreak
\tif selected.is_empty() or not _genetics_recipe_unlocked(selected):
\t\treturn
\tvar min_level: int = int(selected.get("min_level", 1))
\tif grower_level < min_level:
\t\treturn
\tvar parent_a: String = str(selected.get("parent_a", ""))
\tvar parent_b: String = str(selected.get("parent_b", ""))
\tvar a_owned: int = int(seed_inventory.get(parent_a, 0))
\tvar b_owned: int = int(seed_inventory.get(parent_b, 0))
\tif a_owned < 1 or b_owned < 1:
\t\treturn
\tvar output_name: String = str(selected.get("output", ""))
\tvar output_count: int = maxi(1, int(selected.get("count", 2)))
\tseed_inventory[parent_a] = a_owned - 1
\tseed_inventory[parent_b] = b_owned - 1
\tseed_inventory[output_name] = int(seed_inventory.get(output_name, 0)) + output_count
\t_increment_advancement_stat("hybrids_created")
\t_add_progress(30, 5)
\tstatus_label.text = "Genetics discovery: %s. %d hybrid seeds were added to your grow shelf." % [output_name, output_count]
\t_save_game()
\t_refresh_phone()

'''
    pat=r'func _build_genetics_app\(\) -> void:\n.*?(?=func _max_friend_loyalty\(\) -> int:\n)'
    text,n=re.subn(pat,genetics_new,text,count=1,flags=re.S)
    if n!=1:
        raise RuntimeError("genetics app block replacement failed")

    must=[
        '"reward_recipe": "Citrus Velvet"',
        '"reward_recipe": "Cherry Frost"',
        '"reward_recipe": "Ember Berry"',
        '"reward_recipe": "Crown Cake"',
        'func _genetics_recipe_catalog() -> Array[Dictionary]:',
        'seed_inventory[parent_a] = a_owned - 1',
        'seed_inventory[parent_b] = b_owned - 1',
        '"recipe_only": true',
    ]
    for fragment in must:
        if fragment not in text:
            raise RuntimeError("restored genetics fragment missing: "+fragment)
    return text

def patch_genetics_only_seeds(text):
    # Frozen Purple remains in SEED_ORDER/inventory so genetics output, planting,
    # saves, customer demand and progression all continue to work. We only
    # remove direct shop acquisition and shop-facing unlock messaging.
    shop_loop = '''\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
'''
    shop_loop_new = '''\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tif seed_name == "Frozen Purple":
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
'''
    # This exact block appears in the Seeds shop and elsewhere. Limit the
    # replacement to the first occurrence after the shop's NEXT GENETIC label.
    shop_anchor = 'next_unlock.text = "NEXT GENETIC'
    anchor_pos = text.find(shop_anchor)
    if anchor_pos < 0:
        raise RuntimeError("Seeds shop anchor missing")
    loop_pos = text.find(shop_loop, anchor_pos)
    if loop_pos < 0:
        raise RuntimeError("Seeds shop loop missing")
    text = text[:loop_pos] + text[loop_pos:].replace(shop_loop, shop_loop_new, 1)

    next_old = '''func _next_locked_seed_name() -> String:
\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif grower_level < int(info.get("unlock", 1)):
\t\t\treturn seed_name
\treturn ""
'''
    next_new = '''func _next_locked_seed_name() -> String:
\tfor seed_name in SEED_ORDER:
\t\tif not seed_catalog.has(seed_name):
\t\t\tcontinue
\t\tif seed_name == "Frozen Purple":
\t\t\tcontinue
\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif grower_level < int(info.get("unlock", 1)):
\t\t\treturn seed_name
\treturn ""
'''
    if next_old not in text:
        raise RuntimeError("Next locked seed function missing")
    text = text.replace(next_old, next_new, 1)

    buy_old = '''func _buy_seed(seed_name: String) -> void:
\tif tutorial_active:
'''
    buy_new = '''func _buy_seed(seed_name: String) -> void:
\tif seed_name == "Frozen Purple":
\t\tstatus_label.text = "Frozen Purple is genetics-only. Create it in Phone -> Genetics."
\t\treturn
\tif tutorial_active:
'''
    if buy_old not in text:
        raise RuntimeError("Seed purchase function missing")
    text = text.replace(buy_old, buy_new, 1)

    level_old = '''\t\tfor seed_name in SEED_ORDER:
\t\t\tif seed_catalog.has(seed_name):
\t\t\t\tvar seed_info: Dictionary = seed_catalog[seed_name]
\t\t\t\tif int(seed_info.get("unlock", 1)) == grower_level:
\t\t\t\t\tunlocked_names.append(seed_name)
'''
    level_new = '''\t\tfor seed_name in SEED_ORDER:
\t\t\tif seed_name == "Frozen Purple":
\t\t\t\tcontinue
\t\t\tif seed_catalog.has(seed_name):
\t\t\t\tvar seed_info: Dictionary = seed_catalog[seed_name]
\t\t\t\tif int(seed_info.get("unlock", 1)) == grower_level:
\t\t\t\t\tunlocked_names.append(seed_name)
'''
    if level_old not in text:
        raise RuntimeError("Grower unlock message loop missing")
    text = text.replace(level_old, level_new, 1)

    # Genetics recipe itself must remain available and unchanged.
    required = [
        'title.text = "PURPLE DREAM x BLUE FROST"',
        'Discovery: Frozen Purple',
        'cross.pressed.connect(_create_frozen_purple_cross)',
        'seed_inventory["Frozen Purple"] = int(seed_inventory.get("Frozen Purple", 0)) + 2',
    ]
    for fragment in required:
        if fragment not in text:
            raise RuntimeError("Frozen Purple genetics recipe missing: " + fragment)
    return text


def patch_task_markers(text):
    old_story='return "%s %s" % ["OK" if done else "[ ]", text_value]'
    new_story='return "%s %s" % ["[x]" if done else "[ ]", text_value]'
    if old_story not in text:
        raise RuntimeError("story checklist marker missing")
    text=text.replace(old_story,new_story,1)

    old_req='requirement_label.text = "%s %s: %d / %d" % ["OK" if progress_value >= needed else "[ ]", str(requirement.get("label", "Extra goal")), progress_value, needed]'
    new_req='requirement_label.text = "%s %s: %d / %d" % ["[x]" if progress_value >= needed else "[ ]", str(requirement.get("label", "Extra goal")), progress_value, needed]'
    if old_req not in text:
        raise RuntimeError("advancement requirement marker missing")
    text=text.replace(old_req,new_req,1)
    return text


def patch_tent_pot_switching(text):
    # While a direct pot panel is open, allow only plant taps in the current
    # approached tent. This lets the player switch Pot 1/2/3 without closing
    # the panel, while blocking camera/world navigation and panel click-through.
    modal_old='''\tif _any_modal_open():
\t\t_reset_world_pointer()
\t\treturn

\tvar can_room_look: bool = room_ring.has(current_view) or current_view in ["grow", "grow2", "grow3"]
'''
    modal_new='''\tif plant_direct_panel != null and plant_direct_panel.visible and current_view in ["grow", "grow2", "grow3"]:
\t\tif _handle_room_pointer(event, false, false, true):
\t\t\tget_viewport().set_input_as_handled()
\t\treturn
\tif _any_modal_open():
\t\t_reset_world_pointer()
\t\treturn

\tvar can_room_look: bool = room_ring.has(current_view) or current_view in ["grow", "grow2", "grow3"]
'''
    if modal_old not in text:
        raise RuntimeError("input modal gate marker missing")
    text=text.replace(modal_old,modal_new,1)

    pointer_old='''\tfor control: Control in [world_top_bar, view_label, status_label, contextual_button, left_button, right_button, back_button, door_quick_button, tutorial_world_coach]:
'''
    pointer_new='''\tfor control: Control in [world_top_bar, view_label, status_label, contextual_button, left_button, right_button, back_button, door_quick_button, tutorial_world_coach, plant_direct_panel]:
'''
    if pointer_old not in text:
        raise RuntimeError("room UI pointer guard marker missing")
    text=text.replace(pointer_old,pointer_new,1)

    # Keep the current pot panel visible when another pot is selected. Existing
    # _open_direct_plant already replaces selected_plant_slot and refreshes it.
    required=[
        'func _open_direct_plant(slot_index: int) -> void:',
        'selected_plant_slot = slot_index',
        '_refresh_direct_plant_panel()',
        'var can_tap_plants: bool = current_view in ["grow", "grow2", "grow3"]',
    ]
    for fragment in required:
        if fragment not in text:
            raise RuntimeError("direct pot switch guard missing: "+fragment)
    return text

def compact_to_fit(text, max_bytes):
    data=text.encode("utf-8")
    if len(data)<=max_bytes:
        return data
    # Remove comment-only and blank lines only; executable statements and
    # indentation remain untouched.
    lines=text.splitlines(True)
    kept=[ln for ln in lines if not ln.lstrip().startswith("#")]
    data="".join(kept).encode("utf-8")
    if len(data)>max_bytes:
        # Collapse repeated blank lines.
        compact=[]
        prev_blank=False
        for ln in "".join(kept).splitlines(True):
            blank=(ln.strip()=="")
            if blank and prev_blank:
                continue
            compact.append(ln)
            prev_blank=blank
        data="".join(compact).encode("utf-8")
    if len(data)>max_bytes:
        raise RuntimeError("Patched main.gd does not fit stable slot: %d > %d" % (len(data),max_bytes))
    return data

def patch_main(text):
    # Verify the stable customers we are replacing exist.
    for name in EXISTING_CLIENTS:
        if ('"name": "'+name+'"') not in text:
            raise RuntimeError("Stable client missing: "+name)
    text=add_new_clients(text)
    text=patch_peephole(text)
    text=patch_full_genetics(text)
    text=patch_task_markers(text)
    text=patch_tent_pot_switching(text)

    # Guard important known-good systems and Friend Tyler.
    required=[
        "stale_customer_session","_schedule_next_customer(true)",
        "const REEVES_TOTAL_OBLIGATION: int = 8000",
        "func _claim_all_advancements() -> void:",
        '"name": "Tyler"', '"tier": "Friend"',
    ]
    for frag in required:
        if frag not in text:
            raise RuntimeError("Stable guard missing: "+frag)
    if 'OS.is_debug_build() and not reeves_met' in text or 'FORCE REEVES' in text.upper():
        raise RuntimeError("Force Reeves debug detected")
    return text

def write_directory(out, entries):
    out.extend(struct.pack("<I",len(entries)))
    for e in entries:
        raw=e["name"].encode("utf-8")
        plen=align(len(raw),4)
        out.extend(struct.pack("<I",plen))
        out.extend(raw)
        out.extend(b"\0"*(plen-len(raw)))
        out.extend(struct.pack("<Q",e["off"]))
        out.extend(struct.pack("<Q",e["size"]))
        out.extend(e["md5"])
        out.extend(struct.pack("<I",e["flags"]))

def build_pck_surgically():
    original,fb,old_dir,entries=parse_pck(BASE)
    main=next((e for e in entries if e["name"]==TARGET),None)
    if main is None:
        raise RuntimeError("scripts/main.gd missing")

    patched_text=patch_main(main["content"].decode("utf-8"))
    patched=compact_to_fit(patched_text,main["size"])
    # Keep the exact original file slot size/offset. Pad only with whitespace.
    if len(patched)<main["size"]:
        patched += b"\n" + b" "*(main["size"]-len(patched)-1)

    out=bytearray(original)
    main_abs=fb+main["off"]
    out[main_abs:main_abs+main["size"]]=patched
    main["md5"]=hashlib.md5(patched).digest()
    main["content"]=patched

    # Append portrait data after the untouched original PCK. The old directory
    # remains unused; all original file offsets stay identical.
    for client,src_name in PORTRAIT_SOURCE.items():
        packed_name="assets/characters/peephole/%s.webp" % client.lower()
        source=ASSET_DIR/src_name
        if not source.exists():
            raise RuntimeError("Portrait source missing: "+str(source))
        data=source.read_bytes()
        pos=align(len(out),32)
        if pos>len(out):
            out.extend(b"\0"*(pos-len(out)))
        off=pos-fb
        out.extend(data)
        entries.append({
            "name":packed_name,"off":off,"size":len(data),
            "md5":hashlib.md5(data).digest(),"flags":0,"content":data,
        })

    new_dir=align(len(out),32)
    if new_dir>len(out):
        out.extend(b"\0"*(new_dir-len(out)))
    struct.pack_into("<Q",out,32,new_dir)
    write_directory(out,entries)
    OUT.write_bytes(out)

    # Integrity check the finished pack with the same directory reader.
    _,_,_,check=parse_pck(OUT)
    names={e["name"] for e in check}
    for client in PORTRAIT_SOURCE:
        rel="assets/characters/peephole/%s.webp" % client.lower()
        if rel not in names:
            raise RuntimeError("Packed portrait missing: "+rel)

    # Confirm every original resource except main.gd is byte-identical.
    original_map={e["name"]:e for e in parse_pck(BASE)[3]}
    check_map={e["name"]:e for e in check}
    for name,e in original_map.items():
        if name==TARGET:
            continue
        if check_map[name]["md5"]!=e["md5"] or check_map[name]["off"]!=e["off"] or check_map[name]["size"]!=e["size"]:
            raise RuntimeError("Stable resource changed unexpectedly: "+name)

def patch_web_release():
    size=OUT.stat().st_size
    html=(ROOT/"index.html").read_text(encoding="utf-8")
    html,n=re.subn(r'"index-accountsync10\.pck":\d+','"index-accountsync10.pck":%d'%size,html,count=1)
    if n!=1:
        raise RuntimeError("Could not patch cloud-test PCK size")
    (ROOT/"cloud-test/index.html").write_text(html,encoding="utf-8")

    manifest=json.loads((ROOT/"version.json").read_text(encoding="utf-8"))
    manifest["release_id"]="0.7.9-beta.19-accountsync10-cloudtest-tentswitch1"
    features=list(manifest.get("web_features",[]))
    for feature in ["client-portrait-refresh-28","eleven-new-clients","frozen-purple-genetics-only","expanded-genetics-recipes","genetics-reward-tasks","completed-task-x-marker","direct-pot-switching"]:
        if feature not in features:
            features.append(feature)
    manifest["web_features"]=features
    for item in manifest.get("files",[]):
        rel=str(item.get("path",""))
        target=ROOT/"cloud-test"/rel
        if not target.exists():
            raise RuntimeError("cloud-test manifest file missing: "+rel)
        data=target.read_bytes()
        item["size"]=len(data)
        item["sha256"]=hashlib.sha256(data).hexdigest()
    (ROOT/"cloud-test/version.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")

def main():
    build_pck_surgically()
    patch_web_release()
    print(json.dumps({
        "output":str(OUT),
        "size":OUT.stat().st_size,
        "sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "existing_portraits":len(EXISTING_CLIENTS),
        "new_clients":len(NEW_CLIENTS),
        "total_portraits":len(PORTRAIT_SOURCE),
        "method":"stable-offset surgical patch"
    },indent=2))

if __name__=="__main__":
    main()
