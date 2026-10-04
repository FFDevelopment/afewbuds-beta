from pathlib import Path
import struct, hashlib, re, shutil, zipfile, io

ROOT = Path(".")
SRC = ROOT / "index-accountsync10.pck"
DST = ROOT / "cloud-test/index-peephole1.pck"
ZIP = ROOT / "tools/peephole_assets96.zip"
TARGET = "scripts/main.gd"

PORTRAITS = {
    "CJ": "assets/characters/peephole/cj.webp",
    "Dre": "assets/characters/peephole/dre.webp",
    "Eli": "assets/characters/peephole/eli.webp",
    "Nia": "assets/characters/peephole/nia.webp",
    "Rico": "assets/characters/peephole/rico.webp",
    "Sage": "assets/characters/peephole/sage.webp",
    "Jules": "assets/characters/peephole/jules.webp",
    "Ace": "assets/characters/peephole/ace.webp",
}

def align(n, a):
    return (n + a - 1) // a * a

def parse_pck(path):
    blob = path.read_bytes()
    if blob[:4] != b"GDPC":
        raise RuntimeError("Not a Godot PCK")
    file_base = struct.unpack_from("<Q", blob, 24)[0]
    dir_offset = struct.unpack_from("<Q", blob, 32)[0]
    count = struct.unpack_from("<I", blob, dir_offset)[0]
    pos = dir_offset + 4
    entries = []
    for _ in range(count):
        plen = struct.unpack_from("<I", blob, pos)[0]; pos += 4
        raw = blob[pos:pos+plen]; pos += plen
        name = raw.rstrip(b"\0").decode("utf-8")
        off = struct.unpack_from("<Q", blob, pos)[0]; pos += 8
        size = struct.unpack_from("<Q", blob, pos)[0]; pos += 8
        md5 = blob[pos:pos+16]; pos += 16
        flags = struct.unpack_from("<I", blob, pos)[0]; pos += 4
        content = blob[file_base+off:file_base+off+size]
        if hashlib.md5(content).digest() != md5:
            raise RuntimeError("MD5 mismatch: " + name)
        entries.append((name, content, flags))
    return blob, file_base, entries

def patch_customer_line(text, name, rel_path):
    pat = re.compile(r'^\t\{"name": "' + re.escape(name) + r'".*?\},$', re.M)
    m = pat.search(text)
    if not m:
        raise RuntimeError(f"Customer not found: {name}")
    line = m.group(0)
    if '"peephole_art"' in line:
        line = re.sub(r'"peephole_art": "[^"]+"', f'"peephole_art": "res://{rel_path}"', line)
    else:
        line = line[:-2] + f', "peephole_art": "res://{rel_path}"' + line[-2:]
    return text[:m.start()] + line + text[m.end():]

def patch_main(text):
    for name in ["CJ", "Dre", "Eli", "Nia", "Rico", "Sage", "Jules"]:
        text = patch_customer_line(text, name, PORTRAITS[name])

    if re.search(r'^\t\{"name": "Ace"', text, re.M):
        text = patch_customer_line(text, "Ace", PORTRAITS["Ace"])
    else:
        dre_line = re.search(r'^\t\{"name": "Dre".*?\},$', text, re.M)
        if not dre_line:
            raise RuntimeError("Dre insertion anchor missing")
        ace_line = (
            '\t{"name": "Ace", "recognition_visits": 2, "favorite": "Blue Frost", '
            '"fallback_profile": "cool", "flexibility": 0.52, "min_qty": 1, "max_qty": 3, '
            '"tier": "Established", "unlock_level": 6, '
            '"peephole_art": "res://assets/characters/peephole/ace.webp"},'
        )
        text = text[:dre_line.end()] + "\n" + ace_line + text[dre_line.end():]

    old = '''\tvar avatar_path: String = str(current_customer.get("peephole_art", current_customer.get("avatar", "")))
\tif not avatar_path.is_empty() and ResourceLoader.exists(avatar_path):
\t\tvar avatar_resource: Resource = load(avatar_path)
\t\tvar avatar_texture: Texture2D = avatar_resource as Texture2D
\t\tif avatar_texture != null and peephole_portrait != null:
\t\t\tpeephole_portrait.texture = avatar_texture
\t\t\tpeephole_portrait.visible = true
\t\t\tif peephole_silhouette != null:
\t\t\t\tpeephole_silhouette.visible = false
'''
    new = '''\tvar avatar_path: String = str(current_customer.get("peephole_art", current_customer.get("avatar", "")))
\tvar avatar_texture: Texture2D = _load_peephole_texture(avatar_path)
\tif avatar_texture != null and peephole_portrait != null:
\t\tpeephole_portrait.texture = avatar_texture
\t\tpeephole_portrait.visible = true
\t\tif peephole_silhouette != null:
\t\t\tpeephole_silhouette.visible = false
'''
    if old not in text:
        raise RuntimeError("Peephole load block not found")
    text = text.replace(old, new, 1)

    marker = "func _open_peephole() -> void:\n"
    helper = '''func _load_peephole_texture(path: String) -> Texture2D:
\tif path.is_empty():
\t\treturn null
\tvar lower_path: String = path.to_lower()
\tif FileAccess.file_exists(path) and (lower_path.ends_with(".webp") or lower_path.ends_with(".jpeg") or lower_path.ends_with(".png")):
\t\tvar bytes: PackedByteArray = FileAccess.get_file_as_bytes(path)
\t\tvar image: Image = Image.new()
\t\tvar err: Error = image.load_jpg_from_buffer(bytes) if (lower_path.ends_with(".webp") or lower_path.ends_with(".jpeg")) else image.load_png_from_buffer(bytes)
\t\tif err == OK:
\t\t\treturn ImageTexture.create_from_image(image)
\tif ResourceLoader.exists(path):
\t\treturn load(path) as Texture2D
\treturn null

'''
    if marker not in text:
        raise RuntimeError("Peephole function marker missing")
    text = text.replace(marker, helper + marker, 1)

    for name, rel in PORTRAITS.items():
        if f'"name": "{name}"' not in text or f'res://{rel}' not in text:
            raise RuntimeError(f"Missing customer/art mapping: {name}")
    mapped = re.findall(r'"peephole_art": "(res://assets/characters/peephole/[^"]+)"', text)
    if len(mapped) < 8 or len(set(mapped)) < 8:
        raise RuntimeError("Peephole mappings are not one-to-one")
    if "OS.is_debug_build() and not reeves_met" in text or "FORCE REEVES" in text.upper():
        raise RuntimeError("Force Reeves debug regressed into cloud test")
    if "stale_customer_session" not in text or "_schedule_next_customer(true)" not in text:
        raise RuntimeError("accountsync10 customer recovery is missing")
    return text

def build():
    if not SRC.exists() or not ZIP.exists():
        raise RuntimeError("Missing accountsync10 PCK or portrait archive")
    original, file_base, entries = parse_pck(SRC)

    with zipfile.ZipFile(ZIP, "r") as z:
        image_bytes = {}
        for name, rel in PORTRAITS.items():
            key = Path(rel).name
            image_bytes[rel] = z.read(key)

    patched = []
    found = False
    existing_names = {n for n, _, _ in entries}
    for name, content, flags in entries:
        if name == TARGET:
            found = True
            content = patch_main(content.decode("utf-8")).encode("utf-8")
        patched.append((name, content, flags))
    if not found:
        raise RuntimeError("scripts/main.gd not found")

    for rel, data in image_bytes.items():
        if rel in existing_names:
            patched = [(n, data if n == rel else c, f) for n, c, f in patched]
        else:
            patched.append((rel, data, 0))

    out = bytearray(original[:file_base])
    current = 0
    directory = []
    for name, content, flags in patched:
        target = align(current, 32)
        if target > current:
            out.extend(b"\0" * (target - current))
        off = target
        out.extend(content)
        current = off + len(content)
        directory.append((name, off, len(content), hashlib.md5(content).digest(), flags))

    new_dir_offset = align(len(out), 32)
    if new_dir_offset > len(out):
        out.extend(b"\0" * (new_dir_offset - len(out)))
    struct.pack_into("<Q", out, 32, new_dir_offset)
    out.extend(struct.pack("<I", len(directory)))
    for name, off, size, md5, flags in directory:
        raw = name.encode("utf-8")
        plen = align(len(raw), 4)
        out.extend(struct.pack("<I", plen))
        out.extend(raw)
        out.extend(b"\0" * (plen - len(raw)))
        out.extend(struct.pack("<Q", off))
        out.extend(struct.pack("<Q", size))
        out.extend(md5)
        out.extend(struct.pack("<I", flags))

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_bytes(out)

    # Re-parse for integrity and verify every image is inside the PCK.
    _, _, check_entries = parse_pck(DST)
    check_names = {n for n, _, _ in check_entries}
    for rel in PORTRAITS.values():
        if rel not in check_names:
            raise RuntimeError("Portrait not packed: " + rel)

    shutil.copy2(ROOT / "index-accountsync10.js", ROOT / "cloud-test/index.js")
    shutil.copy2(ROOT / "shared/afb-cloud-accountsync10.js", ROOT / "cloud-test/shared/afb-cloud.js")

    html_path = ROOT / "cloud-test/index.html"
    html = html_path.read_text(encoding="utf-8")
    html = re.sub(r'<title>.*?</title>', '<title>AFewBuds 0.7.9-beta.19 • Peephole Test</title>', html, count=1)
    html = re.sub(r'<script src="shared/afb-cloud\.js\?v=[^"]+"></script>', '<script src="shared/afb-cloud.js?v=peephole1"></script>', html, count=1)
    html = re.sub(r'<script src="index\.js\?v=[^"]+"></script>', '<script src="index.js?v=peephole1"></script>', html, count=1)
    size = DST.stat().st_size
    html = re.sub(r'"fileSizes":\{"[^"]+\.pck":\d+,"index\.wasm":37902138\}', f'"fileSizes":{{"index-peephole1.pck":{size},"index.wasm":37902138}}', html, count=1)
    html = re.sub(r'"mainPack":"[^"]+\.pck"', '"mainPack":"index-peephole1.pck"', html, count=1)
    html_path.write_text(html, encoding="utf-8")

    (ROOT / "cloud-test/TEST_BUILD.txt").write_text(
        """AFewBuds cloud test
Baseline: 0.7.9-beta.19-accountsync10
Test: peephole1

- All accountsync10 fixes retained, including customer scheduler recovery.
- Force Reeves debug remains removed.
- New peephole portraits mapped one-to-one:
  CJ -> cj.webp
  Dre -> dre.webp
  Eli -> eli.webp
  Nia -> nia.webp
  Rico -> rico.webp
  Sage -> sage.webp
  Jules -> jules.webp
  Ace -> ace.webp
- Ace is cloud-test-only for now.
- Existing friend portraits/worker face wraps/door art/social art are untouched.
- Main tester build is unchanged.
""",
        encoding="utf-8",
    )
    print("Built", DST, size, hashlib.sha256(DST.read_bytes()).hexdigest())

if __name__ == "__main__":
    build()
