from pathlib import Path
import struct, hashlib, re, json

ROOT = Path('.')
BASE = ROOT / 'cloud-test/index-peephole1.pck'
OUT = ROOT / 'cloud-test/index-peephole-genetics2.pck'
ASSET_DIR = ROOT / 'tools/peephole_remaining160'
INDEX = ROOT / 'cloud-test/index.html'
TARGET = 'scripts/main.gd'

PORTRAITS = {
    'Ashley':'assets/characters/peephole/ashley.webp',
    'Maya':'assets/characters/peephole/maya.webp',
    'Nova':'assets/characters/peephole/nova.webp',
    'Skye':'assets/characters/peephole/skye.webp',
    'Knox':'assets/characters/peephole/knox.webp',
    'Avery':'assets/characters/peephole/avery.webp',
    'Tasha':'assets/characters/peephole/tasha.webp',
    'Kira':'assets/characters/peephole/kira.webp',
    'Zay':'assets/characters/peephole/zay.webp',
    'Bree':'assets/characters/peephole/bree.webp',
    'Tino':'assets/characters/peephole/tino.webp',
}

GENETICS_TASKS = '''\t{"id": "recipe_citrus_velvet", "category": "Genetics", "tier": 2, "title": "Flavor Notes", "description": "Complete a hybrid batch and build a five-variety seed shelf.", "metric": "hybrids_created", "target": 1, "reward_cash": 0, "reward_xp": 90, "reward_rep": 5, "reward_recipe": "Citrus Velvet", "requires": [{"state": "seed_varieties", "target": 5, "label": "Seed varieties"}]},
\t{"id": "recipe_cherry_frost", "category": "Genetics", "tier": 3, "title": "Cold & Sweet", "description": "Create 3 hybrid batches and reach Grower Level 7.", "metric": "hybrids_created", "target": 3, "reward_cash": 0, "reward_xp": 150, "reward_rep": 8, "reward_recipe": "Cherry Frost", "requires": [{"state": "grower_level", "target": 7, "label": "Grower Level"}]},
\t{"id": "recipe_ember_berry", "category": "Genetics", "tier": 3, "title": "Color Theory", "description": "Create 5 hybrid batches and reach Grower Level 9.", "metric": "hybrids_created", "target": 5, "reward_cash": 0, "reward_xp": 200, "reward_rep": 10, "reward_recipe": "Ember Berry", "requires": [{"state": "grower_level", "target": 9, "label": "Grower Level"}]},
\t{"id": "recipe_crown_cake", "category": "Genetics", "tier": 4, "title": "Crown Lab", "description": "Create 8 hybrid batches, reach Grower Level 11, and complete 50 harvests.", "metric": "hybrids_created", "target": 8, "reward_cash": 0, "reward_xp": 300, "reward_rep": 15, "reward_recipe": "Crown Cake", "requires": [{"state": "grower_level", "target": 11, "label": "Grower Level"}, {"metric": "harvests", "target": 50, "label": "Harvests"}]},
'''

def align(n,a): return (n+a-1)//a*a

def parse_pck(path):
    blob=path.read_bytes()
    if blob[:4] != b'GDPC': raise RuntimeError('Not a Godot PCK')
    fb=struct.unpack_from('<Q',blob,24)[0]
    do=struct.unpack_from('<Q',blob,32)[0]
    count=struct.unpack_from('<I',blob,do)[0]
    pos=do+4; entries=[]
    for _ in range(count):
        plen=struct.unpack_from('<I',blob,pos)[0]; pos+=4
        raw=blob[pos:pos+plen]; pos+=plen
        name=raw.rstrip(b'\0').decode('utf-8')
        off=struct.unpack_from('<Q',blob,pos)[0]; pos+=8
        size=struct.unpack_from('<Q',blob,pos)[0]; pos+=8
        md5=blob[pos:pos+16]; pos+=16
        flags=struct.unpack_from('<I',blob,pos)[0]; pos+=4
        content=blob[fb+off:fb+off+size]
        if hashlib.md5(content).digest()!=md5: raise RuntimeError('MD5 mismatch '+name)
        entries.append((name,content,flags))
    return blob,fb,entries

def replace_once(text, old, new, label):
    if old not in text: raise RuntimeError(label+' marker missing')
    return text.replace(old,new,1)

def map_portrait(text,name,rel):
    pat=re.compile(r'^\t\{"name": "'+re.escape(name)+r'".*?\},$',re.M)
    m=pat.search(text)
    if not m: raise RuntimeError('customer missing: '+name)
    line=m.group(0)
    if '"peephole_art"' in line:
        line=re.sub(r'"peephole_art": "[^"]+"',f'"peephole_art": "res://{rel}"',line)
    else:
        line=line[:-2]+f', "peephole_art": "res://{rel}"'+line[-2:]
    return text[:m.start()]+line+text[m.end():]

def patch_genetics(text):
    old_order='const SEED_ORDER: Array[String] = ["Street Green", "Purple Dream", "Citrus Rush", "Blue Frost", "Velvet Haze", "Frozen Purple", "Golden Ember", "Cherry Glow", "Neon Berry", "Moon Cake", "Midnight Crown", "Black Cherry", "Aurora Reserve", "Solar Frost"]'
    new_order='const SEED_ORDER: Array[String] = ["Street Green", "Purple Dream", "Citrus Rush", "Blue Frost", "Velvet Haze", "Frozen Purple", "Golden Ember", "Cherry Glow", "Neon Berry", "Moon Cake", "Midnight Crown", "Black Cherry", "Aurora Reserve", "Solar Frost", "Citrus Velvet", "Cherry Frost", "Ember Berry", "Crown Cake"]'
    text=replace_once(text,old_order,new_order,'seed order')

    inv_old='''\t"Aurora Reserve": 0
}'''
    inv_new='''\t"Aurora Reserve": 0,
\t"Citrus Velvet": 0,
\t"Cherry Frost": 0,
\t"Ember Berry": 0,
\t"Crown Cake": 0
}'''
    text=replace_once(text,inv_old,inv_new,'seed inventory')

    cat_old='''\t"Solar Frost": {"unlock": 14, "cost": 210, "price": 70, "grade": "S+", "profile": "solar", "harvest": 5, "description": "Late-career prestige genetics intended for reserve-level customers."}
}'''
    cat_new='''\t"Solar Frost": {"unlock": 14, "cost": 210, "price": 70, "grade": "S+", "profile": "solar", "harvest": 5, "description": "Late-career prestige genetics intended for reserve-level customers."},
\t"Citrus Velvet": {"unlock": 99, "cost": 0, "price": 34, "grade": "S", "profile": "citrus", "harvest": 8, "recipe_only": true, "description": "A fictional crossbreed unlocked through Story rewards."},
\t"Cherry Frost": {"unlock": 99, "cost": 0, "price": 46, "grade": "S+", "profile": "cherry", "harvest": 6, "recipe_only": true, "description": "A fictional cold-fruit crossbreed unlocked through progression."},
\t"Ember Berry": {"unlock": 99, "cost": 0, "price": 54, "grade": "S+", "profile": "berry", "harvest": 6, "recipe_only": true, "description": "A fictional gold-and-berry crossbreed unlocked through progression."},
\t"Crown Cake": {"unlock": 99, "cost": 0, "price": 63, "grade": "S+", "profile": "luxury", "harvest": 5, "recipe_only": true, "description": "A fictional prestige crossbreed reserved for late-career genetics work."}
}'''
    text=replace_once(text,cat_old,cat_new,'seed catalog')

    adv='''\t{"id": "three_hybrids", "category": "Genetics", "tier": 4, "title": "Breeding Program", "description": "Create 3 hybrid seed batches.", "metric": "hybrids_created", "target": 3, "reward_cash": 100, "reward_xp": 250, "reward_rep": 15},
'''
    text=replace_once(text,adv,adv+GENETICS_TASKS,'genetics advancement')

    reward_vars='''\tvar reward_seed: String = str(entry.get("reward_seed", ""))
\tvar reward_seed_count: int = int(entry.get("reward_seed_count", 0))
'''
    text=replace_once(text,reward_vars,reward_vars+'\tvar reward_recipe: String = str(entry.get("reward_recipe", ""))\n','reward text vars')

    reward_tail_bullet='''\tif not reward_seed.is_empty() and reward_seed_count > 0:
\t\tparts.append("%dx %s seed" % [reward_seed_count, reward_seed])
\treturn "  •  ".join(parts)
'''
    reward_tail_ascii='''\tif not reward_seed.is_empty() and reward_seed_count > 0:
\t\tparts.append("%dx %s seed" % [reward_seed_count, reward_seed])
\treturn "  |  ".join(parts)
'''
    new_tail='''\tif not reward_seed.is_empty() and reward_seed_count > 0:
\t\tparts.append("%dx %s seed" % [reward_seed_count, reward_seed])
\tif not reward_recipe.is_empty():
\t\tparts.append("GENETICS RECIPE: %s" % reward_recipe)
\treturn "  |  ".join(parts)
'''
    if reward_tail_ascii in text: text=text.replace(reward_tail_ascii,new_tail,1)
    elif reward_tail_bullet in text: text=text.replace(reward_tail_bullet,new_tail,1)
    else: raise RuntimeError('reward tail marker missing')

    shop='''\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tvar unlock_level: int = int(info.get("unlock", 1))
'''
    shop_new='''\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif bool(info.get("recipe_only", false)):
\t\t\tcontinue
\t\tvar unlock_level: int = int(info.get("unlock", 1))
'''
    text=replace_once(text,shop,shop_new,'seed shop recipe filter')

    nxt='''\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif grower_level < int(info.get("unlock", 1)):
'''
    nxt_new='''\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif bool(info.get("recipe_only", false)):
\t\t\tcontinue
\t\tif grower_level < int(info.get("unlock", 1)):
'''
    text=replace_once(text,nxt,nxt_new,'next locked seed recipe filter')

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
    if n!=1: raise RuntimeError('genetics app block replacement failed')
    return text

def patch_main(text):
    # peephole1 omitted Tino; restore the current Reserve/Lv14 record first.
    if '"name": "Tino"' not in text:
        anchor = '\t{"name": "Bree"'
        anchor_pos = text.find(anchor)
        if anchor_pos < 0:
            raise RuntimeError("Bree insertion anchor missing for Tino migration")
        line_end = text.find("\n", anchor_pos)
        if line_end < 0:
            raise RuntimeError("Bree customer line has no newline")
        tino = '\t{"name": "Tino", "recognition_visits": 3, "favorite": "Solar Frost", "fallback_profile": "solar", "flexibility": 0.30, "min_qty": 3, "max_qty": 6, "tier": "Reserve", "unlock_level": 14},'
        text = text[:line_end + 1] + tino + "\n" + text[line_end + 1:]

    for name, rel in PORTRAITS.items():
        text = map_portrait(text, name, rel)
    text = patch_genetics(text)

    must = [
        'stale_customer_session', '_schedule_next_customer(true)', 'load_webp_from_buffer',
        'const REEVES_TOTAL_OBLIGATION: int = 8000', 'Use Phone > Heat > LAY LOW',
        'func _claim_all_advancements() -> void:',
        '"reward_recipe": "Citrus Velvet"', '"reward_recipe": "Cherry Frost"',
        '"reward_recipe": "Ember Berry"', '"reward_recipe": "Crown Cake"',
        'func _genetics_recipe_catalog() -> Array[Dictionary]:', 'recipe_only',
        'NEED BOTH PARENT SEEDS', 'seed_inventory[parent_a] = a_owned - 1',
        'seed_inventory[parent_b] = b_owned - 1'
    ]
    for fragment in must:
        if fragment not in text:
            raise RuntimeError('missing required source fragment: ' + fragment)
    if 'OS.is_debug_build() and not reeves_met' in text or 'FORCE REEVES' in text.upper():
        raise RuntimeError('Force Reeves debug regressed')
    for name, rel in PORTRAITS.items():
        if ('"name": "' + name + '"') not in text or ('res://' + rel) not in text:
            raise RuntimeError('missing portrait mapping ' + name)

    refs = re.findall(r'"peephole_art": "(res://assets/characters/peephole/[^"]+)"', text)
    if len(refs) < 19 or len(set(refs)) != len(refs):
        raise RuntimeError('peephole art refs not unique: total=%d unique=%d' % (len(refs), len(set(refs))))
    return text

def build():
    original,fb,entries=parse_pck(BASE)
    extras={}
    for customer in PORTRAITS:
        filename=f"{customer.lower()}.webp"
        source=ASSET_DIR/filename
        if not source.exists():
            raise RuntimeError("portrait asset missing: "+str(source))
        extras[f"assets/characters/peephole/{filename}"]=source.read_bytes()
    if len(extras)!=11: raise RuntimeError('expected 11 portrait files')
    patched=[]; found=False; existing={n for n,_,_ in entries}
    for name,content,flags in entries:
        if name==TARGET:
            found=True; content=patch_main(content.decode('utf-8')).encode('utf-8')
        if name in extras: content=extras[name]
        patched.append((name,content,flags))
    if not found: raise RuntimeError('main.gd missing')
    for name,data in extras.items():
        if name not in existing: patched.append((name,data,0))
    out=bytearray(original[:fb]); cur=0; directory=[]
    for name,content,flags in patched:
        target=align(cur,32)
        if target>cur: out.extend(b'\0'*(target-cur))
        off=target; out.extend(content); cur=off+len(content)
        directory.append((name,off,len(content),hashlib.md5(content).digest(),flags))
    ndo=align(len(out),32)
    if ndo>len(out): out.extend(b'\0'*(ndo-len(out)))
    struct.pack_into('<Q',out,32,ndo); out.extend(struct.pack('<I',len(directory)))
    for name,off,size,md5,flags in directory:
        raw=name.encode(); plen=align(len(raw),4)
        out.extend(struct.pack('<I',plen)); out.extend(raw); out.extend(b'\0'*(plen-len(raw)))
        out.extend(struct.pack('<Q',off)); out.extend(struct.pack('<Q',size)); out.extend(md5); out.extend(struct.pack('<I',flags))
    OUT.write_bytes(out)
    _,_,check=parse_pck(OUT)
    names={n for n,_,_ in check}
    for rel in PORTRAITS.values():
        if rel not in names: raise RuntimeError('packed portrait missing '+rel)
    return len(out),hashlib.sha256(out).hexdigest()

def patch_index(size):
    html=INDEX.read_text()
    html=re.sub(r'<title>.*?</title>','<title>AFewBuds 0.7.9-beta.19 • Peephole + Genetics Test</title>',html,count=1)
    m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
    if not m: raise RuntimeError('GODOT_CONFIG missing')
    cfg=m.group(1)
    cfg=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-peephole-genetics2.pck":{size},"index.wasm":37902138}}',cfg,count=1)
    cfg=re.sub(r'"mainPack":"[^"]+"','"mainPack":"index-peephole-genetics2.pck"',cfg,count=1)
    html=html[:m.start(1)]+cfg+html[m.end(1):]
    html=re.sub(r'index\.js\?v=[^"]+','index.js?v=peepholegenetics2',html,count=1)
    html=re.sub(r'shared/afb-cloud\.js\?v=[^"]+','shared/afb-cloud.js?v=peepholegenetics2',html,count=1)
    INDEX.write_text(html)

def main():
    size,sha=build(); patch_index(size)
    mapping={name:f'res://{rel}' for name,rel in PORTRAITS.items()}
    (ROOT/'cloud-test/TEST_BUILD.txt').write_text(
        'AFewBuds cloud test\nBaseline: 0.7.9-beta.19-accountsync10 / peephole1\nTest: peephole-genetics2\n\n'
        '- Retains accountsync10 cloud/scheduler/Heat/Reeves fixes.\n'
        '- 19 unique non-friend peephole portraits are mapped in the test build.\n'
        '- Remaining 11 mappings: '+json.dumps(mapping,sort_keys=True)+'\n'
        '- Portrait backgrounds were visually reviewed and cleaned of obvious real-world delivery branding/logos.\n'
        '- Genetics task rewards unlock recipes in Phone > Genetics only.\n'
        '- Citrus Velvet = Citrus Rush + Velvet Haze.\n'
        '- Cherry Frost = Cherry Glow + Blue Frost.\n'
        '- Ember Berry = Golden Ember + Neon Berry.\n'
        '- Crown Cake = Midnight Crown + Moon Cake.\n'
        '- Mixing consumes one of each parent and creates two hybrid seeds.\n'
        '- Recipe-only hybrids are hidden from Shop > Seeds.\n'
        '- Main tester root remains unchanged.\n'
        f'- PCK sha256: {sha}\n'
    )
    print(json.dumps({'size':size,'sha256':sha,'portraits':len(PORTRAITS),'output':str(OUT)},indent=2))

if __name__=='__main__': main()
, text, re.M)
        if not bree:
            raise RuntimeError("Bree insertion anchor missing for Tino migration")
        tino='\\t{"name": "Tino", "recognition_visits": 3, "favorite": "Solar Frost", "fallback_profile": "solar", "flexibility": 0.30, "min_qty": 3, "max_qty": 6, "tier": "Reserve", "unlock_level": 14},'
        text=text[:bree.end()]+"\\n"+tino+text[bree.end():]
    for name,rel in PORTRAITS.items(): text=map_portrait(text,name,rel)
    text=patch_genetics(text)
    must=[
        'stale_customer_session','_schedule_next_customer(true)','load_webp_from_buffer',
        'const REEVES_TOTAL_OBLIGATION: int = 8000','Use Phone > Heat > LAY LOW',
        'func _claim_all_advancements() -> void:',
        '"reward_recipe": "Citrus Velvet"','"reward_recipe": "Cherry Frost"',
        '"reward_recipe": "Ember Berry"','"reward_recipe": "Crown Cake"',
        'func _genetics_recipe_catalog() -> Array[Dictionary]:','recipe_only',
        'NEED BOTH PARENT SEEDS','seed_inventory[parent_a] = a_owned - 1',
        'seed_inventory[parent_b] = b_owned - 1'
    ]
    for s in must:
        if s not in text: raise RuntimeError('missing required source fragment: '+s)
    if 'OS.is_debug_build() and not reeves_met' in text or 'FORCE REEVES' in text.upper():
        raise RuntimeError('Force Reeves debug regressed')
    for name,rel in PORTRAITS.items():
        if f'"name": "{name}"' not in text or f'res://{rel}' not in text:
            raise RuntimeError('missing portrait mapping '+name)
    refs=re.findall(r'"peephole_art": "(res://assets/characters/peephole/[^"]+)"',text)
    if len(refs) < 19 or len(set(refs)) != len(refs):
        raise RuntimeError(f'peephole art refs not unique: total={len(refs)} unique={len(set(refs))}')
    return text

def build():
    original,fb,entries=parse_pck(BASE)
    extras={}
    for customer in PORTRAITS:
        filename=f"{customer.lower()}.webp"
        source=ASSET_DIR/filename
        if not source.exists():
            raise RuntimeError("portrait asset missing: "+str(source))
        extras[f"assets/characters/peephole/{filename}"]=source.read_bytes()
    if len(extras)!=11: raise RuntimeError('expected 11 portrait files')
    patched=[]; found=False; existing={n for n,_,_ in entries}
    for name,content,flags in entries:
        if name==TARGET:
            found=True; content=patch_main(content.decode('utf-8')).encode('utf-8')
        if name in extras: content=extras[name]
        patched.append((name,content,flags))
    if not found: raise RuntimeError('main.gd missing')
    for name,data in extras.items():
        if name not in existing: patched.append((name,data,0))
    out=bytearray(original[:fb]); cur=0; directory=[]
    for name,content,flags in patched:
        target=align(cur,32)
        if target>cur: out.extend(b'\0'*(target-cur))
        off=target; out.extend(content); cur=off+len(content)
        directory.append((name,off,len(content),hashlib.md5(content).digest(),flags))
    ndo=align(len(out),32)
    if ndo>len(out): out.extend(b'\0'*(ndo-len(out)))
    struct.pack_into('<Q',out,32,ndo); out.extend(struct.pack('<I',len(directory)))
    for name,off,size,md5,flags in directory:
        raw=name.encode(); plen=align(len(raw),4)
        out.extend(struct.pack('<I',plen)); out.extend(raw); out.extend(b'\0'*(plen-len(raw)))
        out.extend(struct.pack('<Q',off)); out.extend(struct.pack('<Q',size)); out.extend(md5); out.extend(struct.pack('<I',flags))
    OUT.write_bytes(out)
    _,_,check=parse_pck(OUT)
    names={n for n,_,_ in check}
    for rel in PORTRAITS.values():
        if rel not in names: raise RuntimeError('packed portrait missing '+rel)
    return len(out),hashlib.sha256(out).hexdigest()

def patch_index(size):
    html=INDEX.read_text()
    html=re.sub(r'<title>.*?</title>','<title>AFewBuds 0.7.9-beta.19 • Peephole + Genetics Test</title>',html,count=1)
    m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
    if not m: raise RuntimeError('GODOT_CONFIG missing')
    cfg=m.group(1)
    cfg=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-peephole-genetics2.pck":{size},"index.wasm":37902138}}',cfg,count=1)
    cfg=re.sub(r'"mainPack":"[^"]+"','"mainPack":"index-peephole-genetics2.pck"',cfg,count=1)
    html=html[:m.start(1)]+cfg+html[m.end(1):]
    html=re.sub(r'index\.js\?v=[^"]+','index.js?v=peepholegenetics2',html,count=1)
    html=re.sub(r'shared/afb-cloud\.js\?v=[^"]+','shared/afb-cloud.js?v=peepholegenetics2',html,count=1)
    INDEX.write_text(html)

def main():
    size,sha=build(); patch_index(size)
    mapping={name:f'res://{rel}' for name,rel in PORTRAITS.items()}
    (ROOT/'cloud-test/TEST_BUILD.txt').write_text(
        'AFewBuds cloud test\nBaseline: 0.7.9-beta.19-accountsync10 / peephole1\nTest: peephole-genetics2\n\n'
        '- Retains accountsync10 cloud/scheduler/Heat/Reeves fixes.\n'
        '- 19 unique non-friend peephole portraits are mapped in the test build.\n'
        '- Remaining 11 mappings: '+json.dumps(mapping,sort_keys=True)+'\n'
        '- Portrait backgrounds were visually reviewed and cleaned of obvious real-world delivery branding/logos.\n'
        '- Genetics task rewards unlock recipes in Phone > Genetics only.\n'
        '- Citrus Velvet = Citrus Rush + Velvet Haze.\n'
        '- Cherry Frost = Cherry Glow + Blue Frost.\n'
        '- Ember Berry = Golden Ember + Neon Berry.\n'
        '- Crown Cake = Midnight Crown + Moon Cake.\n'
        '- Mixing consumes one of each parent and creates two hybrid seeds.\n'
        '- Recipe-only hybrids are hidden from Shop > Seeds.\n'
        '- Main tester root remains unchanged.\n'
        f'- PCK sha256: {sha}\n'
    )
    print(json.dumps({'size':size,'sha256':sha,'portraits':len(PORTRAITS),'output':str(OUT)},indent=2))

if __name__=='__main__': main()
, text, re.M)
        if not bree:
            raise RuntimeError("Bree insertion anchor missing for Tino migration")
        tino = '\t{"name": "Tino", "recognition_visits": 3, "favorite": "Solar Frost", "fallback_profile": "solar", "flexibility": 0.30, "min_qty": 3, "max_qty": 6, "tier": "Reserve", "unlock_level": 14},'
        text = text[:bree.end()] + "\n" + tino + text[bree.end():]

    for name, rel in PORTRAITS.items():
        text = map_portrait(text, name, rel)
    text = patch_genetics(text)

    must = [
        'stale_customer_session', '_schedule_next_customer(true)', 'load_webp_from_buffer',
        'const REEVES_TOTAL_OBLIGATION: int = 8000', 'Use Phone > Heat > LAY LOW',
        'func _claim_all_advancements() -> void:',
        '"reward_recipe": "Citrus Velvet"', '"reward_recipe": "Cherry Frost"',
        '"reward_recipe": "Ember Berry"', '"reward_recipe": "Crown Cake"',
        'func _genetics_recipe_catalog() -> Array[Dictionary]:', 'recipe_only',
        'NEED BOTH PARENT SEEDS', 'seed_inventory[parent_a] = a_owned - 1',
        'seed_inventory[parent_b] = b_owned - 1'
    ]
    for fragment in must:
        if fragment not in text:
            raise RuntimeError('missing required source fragment: ' + fragment)
    if 'OS.is_debug_build() and not reeves_met' in text or 'FORCE REEVES' in text.upper():
        raise RuntimeError('Force Reeves debug regressed')
    for name, rel in PORTRAITS.items():
        if f'"name": "{name}"' not in text or f'res://{rel}' not in text:
            raise RuntimeError('missing portrait mapping ' + name)

    refs = re.findall(r'"peephole_art": "(res://assets/characters/peephole/[^"]+)"', text)
    if len(refs) < 19 or len(set(refs)) != len(refs):
        raise RuntimeError(f'peephole art refs not unique: total={len(refs)} unique={len(set(refs))}')
    return text

def build():
    original,fb,entries=parse_pck(BASE)
    extras={}
    for customer in PORTRAITS:
        filename=f"{customer.lower()}.webp"
        source=ASSET_DIR/filename
        if not source.exists():
            raise RuntimeError("portrait asset missing: "+str(source))
        extras[f"assets/characters/peephole/{filename}"]=source.read_bytes()
    if len(extras)!=11: raise RuntimeError('expected 11 portrait files')
    patched=[]; found=False; existing={n for n,_,_ in entries}
    for name,content,flags in entries:
        if name==TARGET:
            found=True; content=patch_main(content.decode('utf-8')).encode('utf-8')
        if name in extras: content=extras[name]
        patched.append((name,content,flags))
    if not found: raise RuntimeError('main.gd missing')
    for name,data in extras.items():
        if name not in existing: patched.append((name,data,0))
    out=bytearray(original[:fb]); cur=0; directory=[]
    for name,content,flags in patched:
        target=align(cur,32)
        if target>cur: out.extend(b'\0'*(target-cur))
        off=target; out.extend(content); cur=off+len(content)
        directory.append((name,off,len(content),hashlib.md5(content).digest(),flags))
    ndo=align(len(out),32)
    if ndo>len(out): out.extend(b'\0'*(ndo-len(out)))
    struct.pack_into('<Q',out,32,ndo); out.extend(struct.pack('<I',len(directory)))
    for name,off,size,md5,flags in directory:
        raw=name.encode(); plen=align(len(raw),4)
        out.extend(struct.pack('<I',plen)); out.extend(raw); out.extend(b'\0'*(plen-len(raw)))
        out.extend(struct.pack('<Q',off)); out.extend(struct.pack('<Q',size)); out.extend(md5); out.extend(struct.pack('<I',flags))
    OUT.write_bytes(out)
    _,_,check=parse_pck(OUT)
    names={n for n,_,_ in check}
    for rel in PORTRAITS.values():
        if rel not in names: raise RuntimeError('packed portrait missing '+rel)
    return len(out),hashlib.sha256(out).hexdigest()

def patch_index(size):
    html=INDEX.read_text()
    html=re.sub(r'<title>.*?</title>','<title>AFewBuds 0.7.9-beta.19 • Peephole + Genetics Test</title>',html,count=1)
    m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
    if not m: raise RuntimeError('GODOT_CONFIG missing')
    cfg=m.group(1)
    cfg=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-peephole-genetics2.pck":{size},"index.wasm":37902138}}',cfg,count=1)
    cfg=re.sub(r'"mainPack":"[^"]+"','"mainPack":"index-peephole-genetics2.pck"',cfg,count=1)
    html=html[:m.start(1)]+cfg+html[m.end(1):]
    html=re.sub(r'index\.js\?v=[^"]+','index.js?v=peepholegenetics2',html,count=1)
    html=re.sub(r'shared/afb-cloud\.js\?v=[^"]+','shared/afb-cloud.js?v=peepholegenetics2',html,count=1)
    INDEX.write_text(html)

def main():
    size,sha=build(); patch_index(size)
    mapping={name:f'res://{rel}' for name,rel in PORTRAITS.items()}
    (ROOT/'cloud-test/TEST_BUILD.txt').write_text(
        'AFewBuds cloud test\nBaseline: 0.7.9-beta.19-accountsync10 / peephole1\nTest: peephole-genetics2\n\n'
        '- Retains accountsync10 cloud/scheduler/Heat/Reeves fixes.\n'
        '- 19 unique non-friend peephole portraits are mapped in the test build.\n'
        '- Remaining 11 mappings: '+json.dumps(mapping,sort_keys=True)+'\n'
        '- Portrait backgrounds were visually reviewed and cleaned of obvious real-world delivery branding/logos.\n'
        '- Genetics task rewards unlock recipes in Phone > Genetics only.\n'
        '- Citrus Velvet = Citrus Rush + Velvet Haze.\n'
        '- Cherry Frost = Cherry Glow + Blue Frost.\n'
        '- Ember Berry = Golden Ember + Neon Berry.\n'
        '- Crown Cake = Midnight Crown + Moon Cake.\n'
        '- Mixing consumes one of each parent and creates two hybrid seeds.\n'
        '- Recipe-only hybrids are hidden from Shop > Seeds.\n'
        '- Main tester root remains unchanged.\n'
        f'- PCK sha256: {sha}\n'
    )
    print(json.dumps({'size':size,'sha256':sha,'portraits':len(PORTRAITS),'output':str(OUT)},indent=2))

if __name__=='__main__': main()
, text, re.M)
        if not bree:
            raise RuntimeError("Bree insertion anchor missing for Tino migration")
        tino='\\t{"name": "Tino", "recognition_visits": 3, "favorite": "Solar Frost", "fallback_profile": "solar", "flexibility": 0.30, "min_qty": 3, "max_qty": 6, "tier": "Reserve", "unlock_level": 14},'
        text=text[:bree.end()]+"\\n"+tino+text[bree.end():]
    for name,rel in PORTRAITS.items(): text=map_portrait(text,name,rel)
    text=patch_genetics(text)
    must=[
        'stale_customer_session','_schedule_next_customer(true)','load_webp_from_buffer',
        'const REEVES_TOTAL_OBLIGATION: int = 8000','Use Phone > Heat > LAY LOW',
        'func _claim_all_advancements() -> void:',
        '"reward_recipe": "Citrus Velvet"','"reward_recipe": "Cherry Frost"',
        '"reward_recipe": "Ember Berry"','"reward_recipe": "Crown Cake"',
        'func _genetics_recipe_catalog() -> Array[Dictionary]:','recipe_only',
        'NEED BOTH PARENT SEEDS','seed_inventory[parent_a] = a_owned - 1',
        'seed_inventory[parent_b] = b_owned - 1'
    ]
    for s in must:
        if s not in text: raise RuntimeError('missing required source fragment: '+s)
    if 'OS.is_debug_build() and not reeves_met' in text or 'FORCE REEVES' in text.upper():
        raise RuntimeError('Force Reeves debug regressed')
    for name,rel in PORTRAITS.items():
        if f'"name": "{name}"' not in text or f'res://{rel}' not in text:
            raise RuntimeError('missing portrait mapping '+name)
    refs=re.findall(r'"peephole_art": "(res://assets/characters/peephole/[^"]+)"',text)
    if len(refs) < 19 or len(set(refs)) != len(refs):
        raise RuntimeError(f'peephole art refs not unique: total={len(refs)} unique={len(set(refs))}')
    return text

def build():
    original,fb,entries=parse_pck(BASE)
    extras={}
    for customer in PORTRAITS:
        filename=f"{customer.lower()}.webp"
        source=ASSET_DIR/filename
        if not source.exists():
            raise RuntimeError("portrait asset missing: "+str(source))
        extras[f"assets/characters/peephole/{filename}"]=source.read_bytes()
    if len(extras)!=11: raise RuntimeError('expected 11 portrait files')
    patched=[]; found=False; existing={n for n,_,_ in entries}
    for name,content,flags in entries:
        if name==TARGET:
            found=True; content=patch_main(content.decode('utf-8')).encode('utf-8')
        if name in extras: content=extras[name]
        patched.append((name,content,flags))
    if not found: raise RuntimeError('main.gd missing')
    for name,data in extras.items():
        if name not in existing: patched.append((name,data,0))
    out=bytearray(original[:fb]); cur=0; directory=[]
    for name,content,flags in patched:
        target=align(cur,32)
        if target>cur: out.extend(b'\0'*(target-cur))
        off=target; out.extend(content); cur=off+len(content)
        directory.append((name,off,len(content),hashlib.md5(content).digest(),flags))
    ndo=align(len(out),32)
    if ndo>len(out): out.extend(b'\0'*(ndo-len(out)))
    struct.pack_into('<Q',out,32,ndo); out.extend(struct.pack('<I',len(directory)))
    for name,off,size,md5,flags in directory:
        raw=name.encode(); plen=align(len(raw),4)
        out.extend(struct.pack('<I',plen)); out.extend(raw); out.extend(b'\0'*(plen-len(raw)))
        out.extend(struct.pack('<Q',off)); out.extend(struct.pack('<Q',size)); out.extend(md5); out.extend(struct.pack('<I',flags))
    OUT.write_bytes(out)
    _,_,check=parse_pck(OUT)
    names={n for n,_,_ in check}
    for rel in PORTRAITS.values():
        if rel not in names: raise RuntimeError('packed portrait missing '+rel)
    return len(out),hashlib.sha256(out).hexdigest()

def patch_index(size):
    html=INDEX.read_text()
    html=re.sub(r'<title>.*?</title>','<title>AFewBuds 0.7.9-beta.19 • Peephole + Genetics Test</title>',html,count=1)
    m=re.search(r'const GODOT_CONFIG = (\{.*?\});',html)
    if not m: raise RuntimeError('GODOT_CONFIG missing')
    cfg=m.group(1)
    cfg=re.sub(r'"fileSizes":\{[^}]*\}',f'"fileSizes":{{"index-peephole-genetics2.pck":{size},"index.wasm":37902138}}',cfg,count=1)
    cfg=re.sub(r'"mainPack":"[^"]+"','"mainPack":"index-peephole-genetics2.pck"',cfg,count=1)
    html=html[:m.start(1)]+cfg+html[m.end(1):]
    html=re.sub(r'index\.js\?v=[^"]+','index.js?v=peepholegenetics2',html,count=1)
    html=re.sub(r'shared/afb-cloud\.js\?v=[^"]+','shared/afb-cloud.js?v=peepholegenetics2',html,count=1)
    INDEX.write_text(html)

def main():
    size,sha=build(); patch_index(size)
    mapping={name:f'res://{rel}' for name,rel in PORTRAITS.items()}
    (ROOT/'cloud-test/TEST_BUILD.txt').write_text(
        'AFewBuds cloud test\nBaseline: 0.7.9-beta.19-accountsync10 / peephole1\nTest: peephole-genetics2\n\n'
        '- Retains accountsync10 cloud/scheduler/Heat/Reeves fixes.\n'
        '- 19 unique non-friend peephole portraits are mapped in the test build.\n'
        '- Remaining 11 mappings: '+json.dumps(mapping,sort_keys=True)+'\n'
        '- Portrait backgrounds were visually reviewed and cleaned of obvious real-world delivery branding/logos.\n'
        '- Genetics task rewards unlock recipes in Phone > Genetics only.\n'
        '- Citrus Velvet = Citrus Rush + Velvet Haze.\n'
        '- Cherry Frost = Cherry Glow + Blue Frost.\n'
        '- Ember Berry = Golden Ember + Neon Berry.\n'
        '- Crown Cake = Midnight Crown + Moon Cake.\n'
        '- Mixing consumes one of each parent and creates two hybrid seeds.\n'
        '- Recipe-only hybrids are hidden from Shop > Seeds.\n'
        '- Main tester root remains unchanged.\n'
        f'- PCK sha256: {sha}\n'
    )
    print(json.dumps({'size':size,'sha256':sha,'portraits':len(PORTRAITS),'output':str(OUT)},indent=2))

if __name__=='__main__': main()
