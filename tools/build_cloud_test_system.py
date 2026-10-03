from pathlib import Path
import struct
import hashlib
import re

BASE_PCK = Path("cloud-test/index.pck")
OUT_PCK = Path("cloud-test/index-system.pck")
INDEX_HTML = Path("cloud-test/index.html")
TARGET = "scripts/main.gd"

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
        plen = struct.unpack_from("<I", blob, pos)[0]
        pos += 4
        path_raw = blob[pos:pos + plen]
        pos += plen
        name = path_raw.rstrip(b"\0").decode("utf-8")
        offset = struct.unpack_from("<Q", blob, pos)[0]
        pos += 8
        size = struct.unpack_from("<Q", blob, pos)[0]
        pos += 8
        md5 = blob[pos:pos + 16]
        pos += 16
        flags = struct.unpack_from("<I", blob, pos)[0]
        pos += 4
        content = blob[file_base + offset:file_base + offset + size]
        if hashlib.md5(content).digest() != md5:
            raise RuntimeError(f"MD5 mismatch before rebuild: {name}")
        entries.append((name, content, flags))
    return blob, file_base, entries

def patch_main(text):
    ready_old = "func _ready() -> void:\n\trng.randomize()\n\t_load_game()\n"
    ready_new = "func _ready() -> void:\n\trng.randomize()\n\t_apply_cloud_boot_save()\n\t_load_game()\n"
    if ready_old not in text:
        raise RuntimeError("Ready/load marker not found")
    text = text.replace(ready_old, ready_new, 1)

    cloud_marker = "func _load_game() -> void:\n"
    if cloud_marker not in text:
        raise RuntimeError("Load game marker not found")
    cloud_block = '''func _apply_cloud_boot_save() -> void:
\tif not OS.has_feature("web"):
\t\treturn
\tvar raw_variant: Variant = JavaScriptBridge.eval("window.AFB_CLOUD_BOOT_SAVE || ''", true)
\tif not (raw_variant is String):
\t\treturn
\tvar raw: String = str(raw_variant)
\tif raw.is_empty():
\t\treturn
\tvar parsed: Variant = JSON.parse_string(raw)
\tif not (parsed is Dictionary):
\t\treturn
\tvar file: FileAccess = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
\tif file == null:
\t\treturn
\tfile.store_string(raw)
\tfile.close()
\tJavaScriptBridge.eval("window.AFB_CLOUD_BOOT_SAVE = '';", true)

'''
    text = text.replace(cloud_marker, cloud_block + cloud_marker, 1)
    router_old = '\t\t"heat":\n\t\t\tphone_title.text = "Heat"\n\t\t\t_build_heat_app()\n\t\t_:\n'
    router_new = '\t\t"heat":\n\t\t\tphone_title.text = "Heat"\n\t\t\t_build_heat_app()\n\t\t"system":\n\t\t\tphone_title.text = "System"\n\t\t\t_build_system_app()\n\t\t_:\n'
    if router_old not in text:
        raise RuntimeError("Phone router marker not found")
    text = text.replace(router_old, router_new, 1)

    home_old = '\t_add_phone_app_tile(grid, "", "Stats", "Progress & revenue", "stats")\n\t_add_phone_app_tile(grid, "", "Help", "Basics & controls", "help")\n'
    home_new = '\t_add_phone_app_tile(grid, "", "Stats", "Progress & revenue", "stats")\n\t_add_phone_app_tile(grid, "", "System", "Save game & safe quit", "system")\n\t_add_phone_app_tile(grid, "", "Help", "Basics & controls", "help")\n'
    if home_old not in text:
        raise RuntimeError("Phone home marker not found")
    text = text.replace(home_old, home_new, 1)

    marker = "func _phone_category_grid() -> GridContainer:\n"
    if marker not in text:
        raise RuntimeError("Phone category marker not found")

    block = '''func _build_system_app() -> void:
\tvar intro: Label = Label.new()
\tintro.text = "SAVE & SESSION"
\tintro.add_theme_font_size_override("font_size", 22)
\tphone_list.add_child(intro)

\tvar detail: Label = Label.new()
\tdetail.text = "AFewBuds saves automatically during play. Use SAVE GAME whenever you want an extra manual save before switching devices or closing the game. Signed-in web players are backed up to the same AFewBuds account automatically."
\tdetail.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\tdetail.add_theme_font_size_override("font_size", 17)
\tdetail.modulate = Color("b8c5ca")
\tphone_list.add_child(detail)

\tvar save_card: PanelContainer = PanelContainer.new()
\tsave_card.add_theme_stylebox_override("panel", _style_box(Color("14201a"), Color("3f7654"), 16, 1))
\tphone_list.add_child(save_card)
\tvar save_box: VBoxContainer = VBoxContainer.new()
\tsave_box.add_theme_constant_override("separation", 10)
\tsave_card.add_child(save_box)
\tvar save_title: Label = Label.new()
\tsave_title.text = "Manual save"
\tsave_title.add_theme_font_size_override("font_size", 20)
\tsave_box.add_child(save_title)
\tvar save_note: Label = Label.new()
\tsave_note.text = "Writes your current career to this device immediately. If you are signed in on the web build, that save is then synced to your cloud account in the background."
\tsave_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\tsave_note.modulate = Color("b6c4bc")
\tsave_box.add_child(save_note)
\tvar save_button: Button = Button.new()
\tsave_button.text = "SAVE GAME"
\tsave_button.custom_minimum_size.y = 62
\tsave_button.add_theme_font_size_override("font_size", 19)
\tsave_button.pressed.connect(_phone_manual_save)
\tsave_box.add_child(save_button)

\tvar quit_card: PanelContainer = PanelContainer.new()
\tquit_card.add_theme_stylebox_override("panel", _style_box(Color("201b17"), Color("775f43"), 16, 1))
\tphone_list.add_child(quit_card)
\tvar quit_box: VBoxContainer = VBoxContainer.new()
\tquit_box.add_theme_constant_override("separation", 10)
\tquit_card.add_child(quit_box)
\tvar quit_title: Label = Label.new()
\tquit_title.text = "Sleep / safe quit"
\tquit_title.add_theme_font_size_override("font_size", 20)
\tquit_box.add_child(quit_title)
\tvar quit_note: Label = Label.new()
\tquit_note.text = "Saves first, pauses the day and visitors, and prepares your session to close safely. Existing crops follow the normal away-time rules. Nothing is deleted, and RESUME GAME brings you straight back."
\tquit_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\tquit_note.modulate = Color("c9bdad")
\tquit_box.add_child(quit_note)
\tvar quit_button: Button = Button.new()
\tquit_button.text = "SAVE & SLEEP / QUIT"
\tquit_button.custom_minimum_size.y = 62
\tquit_button.add_theme_font_size_override("font_size", 19)
\tquit_button.pressed.connect(_phone_safe_quit)
\tquit_box.add_child(quit_button)

func _phone_manual_save() -> void:
\t_save_game()
\tstatus_label.text = "Game saved. Cloud backup will update automatically while signed in."
\t_refresh_phone()

func _phone_safe_quit() -> void:
\t_save_game()
\tphone_open = false
\tphone_panel.visible = false
\t_set_world_controls_visible(true)
\t_pause_gameplay("Game saved. It is safe to close AFewBuds now. Resume whenever you return.")

'''
    return text.replace(marker, block + marker, 1)

def rebuild():
    original, file_base, entries = parse_pck(BASE_PCK)
    patched_entries = []
    found = False
    for name, content, flags in entries:
        if name == TARGET:
            found = True
            content = patch_main(content.decode("utf-8")).encode("utf-8")
        patched_entries.append((name, content, flags))
    if not found:
        raise RuntimeError("scripts/main.gd not found in PCK")

    out = bytearray(original[:file_base])
    current = 0
    directory = []
    for name, content, flags in patched_entries:
        target = align(current, 32)
        if target > current:
            out.extend(b"\0" * (target - current))
        offset = target
        out.extend(content)
        current = offset + len(content)
        directory.append((name, offset, len(content), hashlib.md5(content).digest(), flags))

    new_dir_offset = align(len(out), 32)
    if new_dir_offset > len(out):
        out.extend(b"\0" * (new_dir_offset - len(out)))
    struct.pack_into("<Q", out, 32, new_dir_offset)
    out.extend(struct.pack("<I", len(directory)))
    for name, offset, size, md5, flags in directory:
        raw = name.encode("utf-8")
        plen = align(len(raw), 4)
        out.extend(struct.pack("<I", plen))
        out.extend(raw)
        out.extend(b"\0" * (plen - len(raw)))
        out.extend(struct.pack("<Q", offset))
        out.extend(struct.pack("<Q", size))
        out.extend(md5)
        out.extend(struct.pack("<I", flags))

    OUT_PCK.write_bytes(out)
    _, _, check = parse_pck(OUT_PCK)
    if len(check) != len(entries):
        raise RuntimeError("PCK entry count changed")
    return len(out)

def patch_index(pck_size):
    html = INDEX_HTML.read_text()
    html = re.sub(
        r"<title>AFewBuds 0\.7\.9-beta\.19[^<]*</title>",
        "<title>AFewBuds 0.7.9-beta.19 • Cloud + System Test</title>",
        html,
        count=1,
    )

    match = re.search(r"const GODOT_CONFIG = (\{.*?\});", html)
    if not match:
        raise RuntimeError("GODOT_CONFIG not found")
    config = match.group(1)
    config = re.sub(
        r'"fileSizes":\{[^}]*\}',
        f'"fileSizes":{{"index-system.pck":{pck_size},"index.wasm":37902138}}',
        config,
        count=1,
    )
    if '"mainPack"' in config:
        config = re.sub(
            r'"mainPack":"[^"]*"',
            '"mainPack":"index-system.pck"',
            config,
            count=1,
        )
    else:
        config = config.replace(
            '"focusCanvas":true',
            '"focusCanvas":true,"mainPack":"index-system.pck"',
            1,
        )
    config = re.sub(
        r'"serviceWorker":"[^"]*"',
        '"serviceWorker":""',
        config,
        count=1,
    )
    html = html[:match.start(1)] + config + html[match.end(1):]

    html = re.sub(
        r"\nwindow\.addEventListener\('afb-cloud-status'.*?\n\}\);\n",
        "\n",
        html,
        count=1,
        flags=re.S,
    )
    html = html.replace(
        "\n\t\tafbShowCloudTestResult(true, 'career uploaded to Supabase');",
        "",
    )
    html = html.replace(
        "\n\t\tafbShowCloudTestResult(false, String(error && error.message || error));",
        "",
    )
    html = html.replace("index.js?v=cloudsync2", "index.js?v=cloudsync3-system")
    html = html.replace(
        "shared/afb-cloud.js?v=cloudsync2",
        "shared/afb-cloud.js?v=cloudsync3-system",
    )
    INDEX_HTML.write_text(html)

if __name__ == "__main__":
    size = rebuild()
    patch_index(size)
    print(
        "Built",
        OUT_PCK,
        size,
        hashlib.sha256(OUT_PCK.read_bytes()).hexdigest(),
    )
