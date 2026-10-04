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
    manifest["release_id"]="0.7.9-beta.19-accountsync10-cloudtest-portraits2"
    features=list(manifest.get("web_features",[]))
    for feature in ["client-portrait-refresh-28","eleven-new-clients"]:
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
