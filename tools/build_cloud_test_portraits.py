from pathlib import Path
import struct, hashlib, re, json

ROOT = Path(".")
BASE = ROOT / "index-accountsync10.pck"
OUT = ROOT / "cloud-test/index-accountsync10.pck"
ASSET_DIR = ROOT / "tools/peephole_clients96"
TARGET = "scripts/main.gd"

PORTRAITS = {
    "CJ":"cj.webp","Dre":"dre.webp","Eli":"eli.webp","Nia":"nia.webp",
    "Rico":"rico.webp","Sage":"sage.webp","Jules":"jules.webp","Ace":"ace.webp",
    "Ashley":"ashley.webp","Maya":"maya.webp","Nova":"nova.webp","Skye":"skye.webp",
    "Knox":"knox.webp","Avery":"avery.webp","Tasha":"tasha.webp","Kira":"kira.webp",
    "Zay":"zay.webp","Bree":"bree.webp","Tino":"tino.webp",
    "Carmen":"carmen.webp","Simone":"simone.webp","Dani":"dani.webp",
    "Marcus":"marcus.webp","Theo":"theo.webp","Devon":"devon.webp",
    "Omar":"omar.webp","Nico":"nico.webp","Tyler":"tyler.webp",
}

NEW_CLIENTS = [
    {"name":"Carmen","recognition_visits":1,"favorite":"Street Green","fallback_profile":"balanced","flexibility":0.65,"min_qty":1,"max_qty":2,"tier":"New","unlock_level":2},
    {"name":"Marcus","recognition_visits":1,"favorite":"Purple Dream","fallback_profile":"balanced","flexibility":0.62,"min_qty":1,"max_qty":2,"tier":"New","unlock_level":3},
    {"name":"Simone","recognition_visits":2,"favorite":"Citrus Rush","fallback_profile":"citrus","flexibility":0.55,"min_qty":1,"max_qty":3,"tier":"Regular","unlock_level":4},
    {"name":"Dani","recognition_visits":2,"favorite":"Velvet Haze","fallback_profile":"haze","flexibility":0.50,"min_qty":1,"max_qty":3,"tier":"Established","unlock_level":5},
    {"name":"Theo","recognition_visits":2,"favorite":"Golden Ember","fallback_profile":"warm","flexibility":0.45,"min_qty":2,"max_qty":4,"tier":"Established","unlock_level":7},
    {"name":"Devon","recognition_visits":2,"favorite":"Cherry Glow","fallback_profile":"cherry","flexibility":0.48,"min_qty":2,"max_qty":4,"tier":"Established","unlock_level":8},
    {"name":"Omar","recognition_visits":3,"favorite":"Neon Berry","fallback_profile":"berry","flexibility":0.40,"min_qty":2,"max_qty":5,"tier":"Established","unlock_level":9},
    {"name":"Nico","recognition_visits":3,"favorite":"Moon Cake","fallback_profile":"luxury","flexibility":0.36,"min_qty":3,"max_qty":5,"tier":"Premium","unlock_level":11},
    {"name":"Tyler","recognition_visits":3,"favorite":"Midnight Crown","fallback_profile":"luxury","flexibility":0.32,"min_qty":3,"max_qty":6,"tier":"Premium","unlock_level":12},
]

def align(n,a): return (n+a-1)//a*a

def parse_pck(path):
    blob=path.read_bytes()
    if blob[:4] != b"GDPC": raise RuntimeError("Not a Godot PCK")
    fb=struct.unpack_from("<Q",blob,24)[0]
    do=struct.unpack_from("<Q",blob,32)[0]
    count=struct.unpack_from("<I",blob,do)[0]
    pos=do+4; entries=[]
    for _ in range(count):
        plen=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        raw=blob[pos:pos+plen]; pos+=plen
        name=raw.rstrip(b"\0").decode("utf-8")
        off=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        size=struct.unpack_from("<Q",blob,pos)[0]; pos+=8
        md5=blob[pos:pos+16]; pos+=16
        flags=struct.unpack_from("<I",blob,pos)[0]; pos+=4
        content=blob[fb+off:fb+off+size]
        if hashlib.md5(content).digest()!=md5: raise RuntimeError("MD5 mismatch "+name)
        entries.append((name,content,flags))
    return blob,fb,entries

def map_portrait(text,name,filename):
    pat=re.compile(r'^\t\{"name": "'+re.escape(name)+r'".*?\},?$',re.M)
    m=pat.search(text)
    if not m:
        return text, False
    line=m.group(0)
    path="res://assets/characters/peephole/"+filename
    if '"peephole_art"' in line:
        line=re.sub(r'"peephole_art": "[^"]+"','"peephole_art": "'+path+'"',line)
    else:
        comma=line.endswith("},")
        body=line[:-2] if comma else line[:-1]
        line=body+', "peephole_art": "'+path+'"' + ("}," if comma else "}")
    return text[:m.start()]+line+text[m.end():], True

def row(data):
    d=dict(data)
    d["peephole_art"]="res://assets/characters/peephole/"+PORTRAITS[d["name"]]
    parts=[]
    for k,v in d.items():
        if isinstance(v,str): parts.append(json.dumps(k)+": "+json.dumps(v))
        else: parts.append(json.dumps(k)+": "+str(v).lower() if isinstance(v,bool) else json.dumps(k)+": "+str(v))
    return "\t{" + ", ".join(parts) + "},"

def insert_after(text, anchor_name, new_row):
    ms=list(re.finditer(r'^\t\{"name": "'+re.escape(anchor_name)+r'".*?\},?$',text,re.M))
    if not ms: raise RuntimeError("Insertion anchor missing: "+anchor_name)
    m=ms[-1]
    return text[:m.end()]+"\n"+new_row+text[m.end():]

def ensure_loader(text):
    loader='''func _load_peephole_texture(path: String) -> Texture2D:
\tif path.is_empty():
\t\treturn null
\tvar lower_path: String = path.to_lower()
\tif FileAccess.file_exists(path) and (lower_path.ends_with(".webp") or lower_path.ends_with(".jpg") or lower_path.ends_with(".jpeg") or lower_path.ends_with(".png")):
\t\tvar bytes: PackedByteArray = FileAccess.get_file_as_bytes(path)
\t\tvar image: Image = Image.new()
\t\tvar err: Error = ERR_FILE_UNRECOGNIZED
\t\tif lower_path.ends_with(".webp"):
\t\t\terr = image.load_webp_from_buffer(bytes)
\t\telif lower_path.ends_with(".jpg") or lower_path.ends_with(".jpeg"):
\t\t\terr = image.load_jpg_from_buffer(bytes)
\t\telse:
\t\t\terr = image.load_png_from_buffer(bytes)
\t\tif err == OK:
\t\t\treturn ImageTexture.create_from_image(image)
\tif ResourceLoader.exists(path):
\t\treturn load(path) as Texture2D
\treturn null

'''
    pat=r'func _load_peephole_texture\(path: String\) -> Texture2D:\n.*?(?=func _open_peephole\(\) -> void:\n)'
    if re.search(pat,text,flags=re.S):
        return re.sub(pat,loader,text,count=1,flags=re.S)
    marker='func _open_peephole() -> void:\n'
    if marker not in text: raise RuntimeError("Peephole open function missing")
    # If the open function still uses ResourceLoader directly, switch only the texture-loading lines.
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
\tvar avatar_texture: Texture2D = _load_peephole_texture(avatar_path)
\tif avatar_texture != null and peephole_portrait != null:
\t\tpeephole_portrait.texture = avatar_texture
\t\tpeephole_portrait.visible = true
\t\tif peephole_silhouette != null:
\t\t\tpeephole_silhouette.visible = false
'''
    if old in text:
        text=text.replace(old,new,1)
    return text.replace(marker,loader+marker,1)

def patch_main(text):
    # Existing customer mappings. Add Ace/Tino only if the current stable catalog lacks them.
    for name in ["CJ","Dre","Eli","Nia","Rico","Sage","Jules","Ashley","Maya","Nova","Skye","Knox","Avery","Tasha","Kira","Zay","Bree"]:
        text,found=map_portrait(text,name,PORTRAITS[name])
        if not found: raise RuntimeError("Stable customer missing: "+name)

    text,found=map_portrait(text,"Ace",PORTRAITS["Ace"])
    if not found:
        ace={"name":"Ace","recognition_visits":2,"favorite":"Blue Frost","fallback_profile":"cool","flexibility":0.52,"min_qty":1,"max_qty":3,"tier":"Established","unlock_level":6}
        text=insert_after(text,"Dre",row(ace))

    text,found=map_portrait(text,"Tino",PORTRAITS["Tino"])
    if not found:
        tino={"name":"Tino","recognition_visits":3,"favorite":"Solar Frost","fallback_profile":"solar","flexibility":0.30,"min_qty":3,"max_qty":6,"tier":"Reserve","unlock_level":14}
        text=insert_after(text,"Bree",row(tino))

    anchor="Tino"
    for c in NEW_CLIENTS:
        text,found=map_portrait(text,c["name"],PORTRAITS[c["name"]])
        if not found:
            text=insert_after(text,anchor,row(c))
            anchor=c["name"]

    text=ensure_loader(text)

    # Guard against accidentally changing unrelated stable systems.
    required=["stale_customer_session","_schedule_next_customer(true)","const REEVES_TOTAL_OBLIGATION: int = 8000","func _claim_all_advancements() -> void:"]
    for frag in required:
        if frag not in text: raise RuntimeError("Stable system guard missing: "+frag)
    if 'OS.is_debug_build() and not reeves_met' in text or 'FORCE REEVES' in text.upper():
        raise RuntimeError("Force Reeves debug detected")

    for name,fn in PORTRAITS.items():
        if ('"name": "'+name+'"') not in text: raise RuntimeError("Client missing: "+name)
        if ('res://assets/characters/peephole/'+fn) not in text: raise RuntimeError("Portrait missing: "+name)
    return text

def build():
    original,fb,entries=parse_pck(BASE)
    extras={}
    for fn in PORTRAITS.values():
        p=ASSET_DIR/fn
        if not p.exists(): raise RuntimeError("Portrait source missing: "+str(p))
        extras["assets/characters/peephole/"+fn]=p.read_bytes()

    patched=[]; found=False; existing={n for n,_,_ in entries}
    for name,content,flags in entries:
        if name==TARGET:
            found=True
            content=patch_main(content.decode("utf-8")).encode("utf-8")
        if name in extras:
            content=extras[name]
        patched.append((name,content,flags))
    if not found: raise RuntimeError("scripts/main.gd missing from stable PCK")
    for name,data in extras.items():
        if name not in existing: patched.append((name,data,0))

    out=bytearray(original[:fb]); cur=0; directory=[]
    for name,content,flags in patched:
        target=align(cur,32)
        if target>cur: out.extend(b"\0"*(target-cur))
        off=target; out.extend(content); cur=off+len(content)
        directory.append((name,off,len(content),hashlib.md5(content).digest(),flags))
    ndo=align(len(out),32)
    if ndo>len(out): out.extend(b"\0"*(ndo-len(out)))
    struct.pack_into("<Q",out,32,ndo)
    out.extend(struct.pack("<I",len(directory)))
    for name,off,size,md5,flags in directory:
        raw=name.encode(); plen=align(len(raw),4)
        out.extend(struct.pack("<I",plen)); out.extend(raw); out.extend(b"\0"*(plen-len(raw)))
        out.extend(struct.pack("<Q",off)); out.extend(struct.pack("<Q",size)); out.extend(md5); out.extend(struct.pack("<I",flags))
    OUT.write_bytes(out)

    _,_,check=parse_pck(OUT)
    names={n for n,_,_ in check}
    for fn in PORTRAITS.values():
        rel="assets/characters/peephole/"+fn
        if rel not in names: raise RuntimeError("Packed portrait missing: "+rel)
    print(json.dumps({"output":str(OUT),"size":OUT.stat().st_size,"sha256":hashlib.sha256(OUT.read_bytes()).hexdigest(),"portraits":28,"new_clients":9},indent=2))

if __name__=="__main__":
    build()
