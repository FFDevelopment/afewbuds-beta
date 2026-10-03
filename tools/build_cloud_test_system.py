from pathlib import Path
import struct
import hashlib
import re

BASE_PCK = Path("cloud-test/index.pck")
OUT_PCK = Path("cloud-test/index-system-malikgen1.pck")
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
    toast_var_marker = "var reset_message: Label\n"
    if toast_var_marker not in text:
        raise RuntimeError("Save notification variable marker not found")
    text = text.replace(
        toast_var_marker,
        toast_var_marker + "var save_notice_panel: PanelContainer\nvar save_notice_title: Label\nvar save_notice_detail: Label\nvar save_notice_timer: Timer\n",
        1,
    )

    router_old = '\t\t"heat":\n\t\t\tphone_title.text = "Heat"\n\t\t\t_build_heat_app()\n\t\t_:\n'
    router_new = '\t\t"heat":\n\t\t\tphone_title.text = "Heat"\n\t\t\t_build_heat_app()\n\t\t"system":\n\t\t\tphone_title.text = "System"\n\t\t\t_build_system_app()\n\t\t_:\n'
    if router_old not in text:
        raise RuntimeError("Phone router marker not found")
    text = text.replace(router_old, router_new, 1)

    ui_call_marker = "\t_build_reset_confirmation()\n"
    if ui_call_marker not in text:
        raise RuntimeError("Save notification UI call marker not found")
    text = text.replace(ui_call_marker, ui_call_marker + "\t_build_save_notification()\n", 1)

    phone_hud_old = '''\tvar phone_button: Button = Button.new()
\tphone_button.text = "PHONE"
\tphone_button.custom_minimum_size = Vector2(124, 48)
\tphone_button.pressed.connect(_toggle_phone)
\ttop_row.add_child(phone_button)
'''
    phone_hud_new = '''\tvar phone_button: Button = Button.new()
\tphone_button.text = "PHONE"
\tphone_button.custom_minimum_size = Vector2(140, 52)
\tphone_button.add_theme_font_size_override("font_size", 18)
\tphone_button.add_theme_color_override("font_color", Color("effff3"))
\tphone_button.add_theme_color_override("font_hover_color", Color("ffffff"))
\tphone_button.add_theme_stylebox_override("normal", _style_box(Color("1b3324"), Color("78c98a"), 13, 2))
\tphone_button.add_theme_stylebox_override("hover", _style_box(Color("274b34"), Color("9be0aa"), 13, 2))
\tphone_button.add_theme_stylebox_override("pressed", _style_box(Color("13271b"), Color("5dac70"), 13, 2))
\tphone_button.tooltip_text = "Open phone"
\tphone_button.pressed.connect(_toggle_phone)
\ttop_row.add_child(phone_button)
'''
    if phone_hud_old not in text:
        raise RuntimeError("HUD phone button marker not found")
    text = text.replace(phone_hud_old, phone_hud_new, 1)

    home_old = '\t_add_phone_app_tile(grid, "", "Stats", "Progress & revenue", "stats")\n\t_add_phone_app_tile(grid, "", "Help", "Basics & controls", "help")\n'
    home_new = '\t_add_phone_app_tile(grid, "", "Stats", "Progress & revenue", "stats")\n\t_add_phone_app_tile(grid, "", "System", "Save game & safe quit", "system")\n\t_add_phone_app_tile(grid, "", "Help", "Basics & controls", "help")\n'
    if home_old not in text:
        raise RuntimeError("Phone home marker not found")
    text = text.replace(home_old, home_new, 1)

    claim_summary_old = '''\tsummary.modulate = Color("d7c28a") if ready_count > 0 else Color("9fb0ba")
\tsummary_box.add_child(summary)

\tvar hint: Label = Label.new()
'''
    claim_summary_new = '''\tsummary.modulate = Color("d7c28a") if ready_count > 0 else Color("9fb0ba")
\tsummary_box.add_child(summary)
\tif ready_count > 0:
\t\tvar claim_all: Button = Button.new()
\t\tclaim_all.text = "CLAIM ALL (%d)" % ready_count
\t\tclaim_all.custom_minimum_size.y = 54
\t\tclaim_all.add_theme_font_size_override("font_size", 18)
\t\tclaim_all.add_theme_stylebox_override("normal", _style_box(Color("1b3324"), Color("78c98a"), 12, 2))
\t\tclaim_all.add_theme_stylebox_override("hover", _style_box(Color("274b34"), Color("9be0aa"), 12, 2))
\t\tclaim_all.add_theme_stylebox_override("pressed", _style_box(Color("13271b"), Color("5dac70"), 12, 2))
\t\tclaim_all.pressed.connect(_claim_all_advancements)
\t\tsummary_box.add_child(claim_all)

\tvar hint: Label = Label.new()
'''
    if claim_summary_old not in text:
        raise RuntimeError("Rewards summary marker not found")
    text = text.replace(claim_summary_old, claim_summary_new, 1)

    claim_func_marker = "func _increment_advancement_stat(metric_name: String, amount: int = 1) -> void:\n"
    if claim_func_marker not in text:
        raise RuntimeError("Advancement claim function marker not found")
    claim_all_block = '''func _claim_all_advancements() -> void:
\tvar ready_entries: Array[Dictionary] = []
\tfor entry: Dictionary in advancement_catalog:
\t\tvar advancement_id: String = str(entry.get("id", ""))
\t\tif advancement_id.is_empty():
\t\t\tcontinue
\t\tif bool(advancement_claimed.get(advancement_id, false)):
\t\t\tcontinue
\t\tif _advancement_is_ready(entry):
\t\t\tready_entries.append(entry)
\tif ready_entries.is_empty():
\t\treturn

\tvar total_cash: int = 0
\tvar total_xp: int = 0
\tvar total_rep: int = 0
\tvar total_fertilizer: int = 0
\tvar seed_totals: Dictionary = {}
\tfor entry: Dictionary in ready_entries:
\t\tvar advancement_id: String = str(entry.get("id", ""))
\t\tadvancement_claimed[advancement_id] = true
\t\ttotal_cash += int(entry.get("reward_cash", 0))
\t\ttotal_xp += int(entry.get("reward_xp", 0))
\t\ttotal_rep += int(entry.get("reward_rep", 0))
\t\ttotal_fertilizer += int(entry.get("reward_fertilizer", 0))
\t\tvar reward_seed: String = str(entry.get("reward_seed", ""))
\t\tvar reward_seed_count: int = int(entry.get("reward_seed_count", 0))
\t\tif not reward_seed.is_empty() and reward_seed_count > 0:
\t\t\tseed_totals[reward_seed] = int(seed_totals.get(reward_seed, 0)) + reward_seed_count

\tcash += total_cash
\tfertilizer_units += total_fertilizer
\tfor seed_name: String in seed_totals.keys():
\t\tseed_inventory[seed_name] = int(seed_inventory.get(seed_name, 0)) + int(seed_totals[seed_name])
\t_add_progress(total_xp, total_rep)
\t_update_cash_ui()
\tstatus_label.text = "Claimed %d completed rewards." % ready_entries.size()
\t_save_game()
\t_refresh_phone()

'''
    text = text.replace(claim_func_marker, claim_all_block + claim_func_marker, 1)

    toast_func_marker = "func _build_pause_overlay() -> void:\n"
    if toast_func_marker not in text:
        raise RuntimeError("Save notification function marker not found")
    toast_block = '''func _build_save_notification() -> void:
\tvar layer: CanvasLayer = CanvasLayer.new()
\tlayer.name = "SaveNotificationLayer"
\tlayer.layer = 40
\tadd_child(layer)
\tvar root: Control = Control.new()
\troot.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
\troot.mouse_filter = Control.MOUSE_FILTER_IGNORE
\tlayer.add_child(root)
\tvar center: CenterContainer = CenterContainer.new()
\tcenter.set_anchors_preset(Control.PRESET_TOP_WIDE)
\tcenter.offset_top = 26
\tcenter.offset_bottom = 110
\tcenter.mouse_filter = Control.MOUSE_FILTER_IGNORE
\troot.add_child(center)
\tsave_notice_panel = PanelContainer.new()
\tsave_notice_panel.custom_minimum_size = Vector2(390, 72)
\tsave_notice_panel.add_theme_stylebox_override("panel", _style_box(Color("14251b"), Color("68bd7d"), 16, 2))
\tsave_notice_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
\tsave_notice_panel.visible = false
\tcenter.add_child(save_notice_panel)
\tvar box: VBoxContainer = VBoxContainer.new()
\tbox.add_theme_constant_override("separation", 2)
\tbox.mouse_filter = Control.MOUSE_FILTER_IGNORE
\tsave_notice_panel.add_child(box)
\tsave_notice_title = Label.new()
\tsave_notice_title.text = "GAME SAVED"
\tsave_notice_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\tsave_notice_title.add_theme_font_size_override("font_size", 21)
\tsave_notice_title.modulate = Color("e8fff0")
\tsave_notice_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
\tbox.add_child(save_notice_title)
\tsave_notice_detail = Label.new()
\tsave_notice_detail.text = "Your career is safe."
\tsave_notice_detail.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
\tsave_notice_detail.add_theme_font_size_override("font_size", 15)
\tsave_notice_detail.modulate = Color("bcd6c4")
\tsave_notice_detail.mouse_filter = Control.MOUSE_FILTER_IGNORE
\tbox.add_child(save_notice_detail)
\tsave_notice_timer = Timer.new()
\tsave_notice_timer.one_shot = true
\tsave_notice_timer.wait_time = 2.4
\tsave_notice_timer.timeout.connect(_hide_save_notification)
\tadd_child(save_notice_timer)

func _show_save_notification(title_text: String = "GAME SAVED", detail_text: String = "Your career is safe.") -> void:
\tif save_notice_panel == null:
\t\treturn
\tsave_notice_title.text = title_text
\tsave_notice_detail.text = detail_text
\tsave_notice_panel.visible = true
\tif save_notice_timer != null:
\t\tsave_notice_timer.stop()
\t\tsave_notice_timer.start()

func _hide_save_notification() -> void:
\tif save_notice_panel != null:
\t\tsave_notice_panel.visible = false

'''
    text = text.replace(toast_func_marker, toast_block + toast_func_marker, 1)

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
\t_show_save_notification("GAME SAVED", "Saved locally. Cloud backup updates automatically while signed in.")
\t_refresh_phone()

func _phone_safe_quit() -> void:
\t_save_game()
\t_show_save_notification("GAME SAVED", "Career saved. AFewBuds is safe to close.")
\tphone_open = false
\tphone_panel.visible = false
\t_set_world_controls_visible(true)
\t_pause_gameplay("Game saved. It is safe to close AFewBuds now. Resume whenever you return.")

'''
    text = text.replace(marker, block + marker, 1)

    # Heat / Reeves completion pass.
    heat_vars_old = '''var raid_warning_day: int = -1
var raids_survived: int = 0
var last_raid_day: int = -1
var raid_lockdown_until_day: int = 0
'''
    heat_vars_new = '''var raid_warning_day: int = -1
var raids_survived: int = 0
var last_raid_day: int = -1
var raid_lockdown_until_day: int = 0
var reeves_last_payment_day: int = -1
var reeves_last_missed_day: int = -1
var enforcement_report_pending: bool = false
var last_enforcement_report: String = ""
'''
    if heat_vars_old not in text:
        raise RuntimeError("Heat state variable marker not found")
    text = text.replace(heat_vars_old, heat_vars_new, 1)

    chapter3_old = '''\t\tand lifetime_revenue >= 5000 \\
\t\tand heat_peak >= 25.0 \\
\t\tand heat_reduced_total >= 10.0
'''
    chapter3_new = '''\t\tand lifetime_revenue >= 5000 \\
\t\tand heat_peak >= 25.0 \\
\t\tand heat_reduced_total >= 10.0 \\
\t\tand reeves_met
'''
    if chapter3_old not in text:
        raise RuntimeError("Chapter 3 completion marker not found")
    text = text.replace(chapter3_old, chapter3_new, 1)

    early_pay_old = '''func _pay_reeves_due(early: bool = false) -> void:
\tvar amount: int = _reeves_payment_amount()
\tif cash < amount:
\t\tsale_body.text = "You need $%d to make this payment." % amount if sale_panel != null and sale_panel.visible else sale_body.text
\t\tstatus_label.text = "You need $%d for the Reeves payment." % amount
\t\treturn
\tcash -= amount
\t_record_daily_expense("Reeves payment", amount)
\treeves_total_paid += amount
\treeves_next_payment_day = game_day + REEVES_PAYMENT_INTERVAL_DAYS
\treeves_missed_payments = 0
\treeves_relationship = mini(100, reeves_relationship + 4)
\tenforcement_risk = maxf(0.0, enforcement_risk - 15.0)
\t_increment_advancement_stat("reeves_payments")
\t_update_cash_ui()
\tstatus_label.text = "Reeves payment made%s. Next payment: Day %d." % [" early" if early else "", reeves_next_payment_day]
\tif not early:
\t\t_end_reeves_visit()
\telse:
\t\t_save_game()
\t\t_refresh_phone()
'''
    early_pay_new = '''func _pay_reeves_due(early: bool = false) -> void:
\tif early and reeves_last_payment_day == game_day:
\t\tstatus_label.text = "You already prepaid Reeves today. Next payment: Day %d." % reeves_next_payment_day
\t\treturn
\tvar amount: int = _reeves_payment_amount()
\tif cash < amount:
\t\tsale_body.text = "You need $%d to make this payment." % amount if sale_panel != null and sale_panel.visible else sale_body.text
\t\tstatus_label.text = "You need $%d for the Reeves payment." % amount
\t\treturn
\tcash -= amount
\t_record_daily_expense("Reeves payment", amount)
\treeves_total_paid += amount
\treeves_last_payment_day = game_day
\treeves_next_payment_day = maxi(game_day, reeves_next_payment_day) + REEVES_PAYMENT_INTERVAL_DAYS
\treeves_missed_payments = 0
\treeves_relationship = mini(100, reeves_relationship + 4)
\tenforcement_risk = maxf(0.0, enforcement_risk - 15.0)
\t_increment_advancement_stat("reeves_payments")
\t_update_cash_ui()
\tstatus_label.text = "Reeves payment made%s. Next payment: Day %d." % [" early" if early else "", reeves_next_payment_day]
\tif not early:
\t\t_end_reeves_visit()
\telse:
\t\t_save_game()
\t\t_refresh_phone()
'''
    if early_pay_old not in text:
        raise RuntimeError("Reeves payment marker not found")
    text = text.replace(early_pay_old, early_pay_new, 1)

    miss_old = '''func _miss_reeves_payment() -> void:
\treeves_missed_payments += 1
\t_increment_advancement_stat("reeves_missed_payments")
\tenforcement_risk = clampf(enforcement_risk + 24.0, 0.0, 100.0)
\treeves_relationship = maxi(0, reeves_relationship - 12)
\treeves_next_payment_day = game_day + 1
\tif reeves_missed_payments >= 2 or enforcement_risk >= RAID_RISK_WARNING_THRESHOLD:
\t\traid_warning_day = game_day
\t\t_log_heat_event("Reeves says the arrangement is no longer protecting you. Raid risk is high.")
\telse:
\t\t_log_heat_event("You missed a Reeves payment. Protection is suspended until you catch up.")
\tstatus_label.text = "Reeves payment missed. Enforcement risk: %d%%." % int(round(enforcement_risk))
\t_end_reeves_visit()
'''
    miss_new = '''func _miss_reeves_payment() -> void:
\tif reeves_last_missed_day == game_day:
\t\tstatus_label.text = "This Reeves payment period is already recorded as missed."
\t\t_end_reeves_visit()
\t\treturn
\treeves_last_missed_day = game_day
\treeves_missed_payments += 1
\t_increment_advancement_stat("reeves_missed_payments")
\tenforcement_risk = clampf(enforcement_risk + 24.0, 0.0, 100.0)
\treeves_relationship = maxi(0, reeves_relationship - 12)
\treeves_next_payment_day = game_day + 1
\tif reeves_missed_payments >= 2 or enforcement_risk >= RAID_RISK_WARNING_THRESHOLD:
\t\traid_warning_day = game_day
\t\t_log_heat_event("Reeves says the arrangement is no longer protecting you. Raid risk is high.")
\telse:
\t\t_log_heat_event("You missed a Reeves payment. Protection is suspended until you catch up.")
\tstatus_label.text = "Reeves payment missed. Enforcement risk: %d%%." % int(round(enforcement_risk))
\t_end_reeves_visit()
'''
    if miss_old not in text:
        raise RuntimeError("Reeves miss marker not found")
    text = text.replace(miss_old, miss_new, 1)

    timeout_old = '''\tif str(current_customer.get("special", "")) == "reeves":
\t\tcustomer_departing = true
\t\tenforcement_risk = clampf(enforcement_risk + 10.0, 0.0, 100.0)
\t\t_log_heat_event("Reeves waited at the door and left irritated. Enforcement risk increased.")
\t\tstatus_label.text = "You ignored Reeves. Enforcement risk increased."
\t\t_queue_customer_exit()
\t\t_save_game()
\t\treturn
'''
    timeout_new = '''\tif str(current_customer.get("special", "")) == "reeves":
\t\tif reeves_visit_reason == "payment_due" or _reeves_payment_overdue():
\t\t\t_log_heat_event("You ignored Reeves on a due-payment visit. The payment was recorded as missed.")
\t\t\t_miss_reeves_payment()
\t\t\treturn
\t\tcustomer_departing = true
\t\tenforcement_risk = clampf(enforcement_risk + 10.0, 0.0, 100.0)
\t\traid_warning_day = game_day if enforcement_risk >= RAID_RISK_WARNING_THRESHOLD else raid_warning_day
\t\t_log_heat_event("Reeves waited at the door and left irritated. Enforcement risk increased.")
\t\tstatus_label.text = "You ignored Reeves. Enforcement risk increased."
\t\t_queue_customer_exit()
\t\t_save_game()
\t\treturn
'''
    if timeout_old not in text:
        raise RuntimeError("Reeves timeout marker not found")
    text = text.replace(timeout_old, timeout_new, 1)

    # Payment negotiation should also advance from the paid-through day and be one payment per day.
    negotiated_due_old = '''\t\t\t\treeves_total_paid += negotiated_due
\t\t\t\treeves_next_payment_day = game_day + REEVES_PAYMENT_INTERVAL_DAYS
\t\t\t\treeves_missed_payments = 0
'''
    negotiated_due_new = '''\t\t\t\treeves_total_paid += negotiated_due
\t\t\t\treeves_last_payment_day = game_day
\t\t\t\treeves_next_payment_day = maxi(game_day, reeves_next_payment_day) + REEVES_PAYMENT_INTERVAL_DAYS
\t\t\t\treeves_missed_payments = 0
'''
    if negotiated_due_old not in text:
        raise RuntimeError("Negotiated Reeves due marker not found")
    text = text.replace(negotiated_due_old, negotiated_due_new, 1)

    raid_report_old = '''\traid_warning_day = -1
\t_log_heat_event("Raid-style enforcement event: %dg inventory and $%d cash lost. Operation closed until Day %d." % [lost_units, seized_cash, raid_lockdown_until_day])
\tstatus_label.text = "ENFORCEMENT EVENT • Lost %dg inventory and $%d. The operation is shut down until Day %d." % [lost_units, seized_cash, raid_lockdown_until_day]
\t_update_cash_ui()
\t_save_game()
'''
    raid_report_new = '''\traid_warning_day = -1
\tlast_enforcement_report = "Day %d: Lost %dg inventory and $%d cash. Reputation -10. Dealers and production staff were sent off duty. Operation locked until Day %d." % [game_day, lost_units, seized_cash, raid_lockdown_until_day]
\tenforcement_report_pending = true
\t_log_heat_event("Raid-style enforcement event: %dg inventory and $%d cash lost. Operation closed until Day %d." % [lost_units, seized_cash, raid_lockdown_until_day])
\tstatus_label.text = "ENFORCEMENT EVENT - Lost %dg inventory and $%d. The operation is shut down until Day %d." % [lost_units, seized_cash, raid_lockdown_until_day]
\t_update_cash_ui()
\t_save_game()
'''
    if raid_report_old not in text:
        raise RuntimeError("Raid report marker not found")
    text = text.replace(raid_report_old, raid_report_new, 1)

    day_status_old = '''\tstatus_label.text = "Day %d started. Dealer settlement complete%s." % [game_day, " • dealer balance still due" if dealer_balance_due > 0 else ""]
\t_save_game()
'''
    day_status_new = '''\tif last_raid_day != game_day:
\t\tstatus_label.text = "Day %d started. Dealer settlement complete%s." % [game_day, " - dealer balance still due" if dealer_balance_due > 0 else ""]
\t_save_game()
'''
    if day_status_old not in text:
        raise RuntimeError("Day-start status marker not found")
    text = text.replace(day_status_old, day_status_new, 1)

    heat_events_marker = '''\tvar events_header: Label = Label.new()
\tevents_header.text = "RECENT PRESSURE"
'''
    heat_report_block = '''\tif enforcement_report_pending and not last_enforcement_report.is_empty():
\t\tvar report_card: PanelContainer = PanelContainer.new()
\t\treport_card.add_theme_stylebox_override("panel", _style_box(Color("281b1b"), Color("c26a5d"), 16, 2))
\t\tphone_list.add_child(report_card)
\t\tvar report_box: VBoxContainer = VBoxContainer.new()
\t\treport_box.add_theme_constant_override("separation", 7)
\t\treport_card.add_child(report_box)
\t\tvar report_title: Label = Label.new()
\t\treport_title.text = "ENFORCEMENT EVENT REPORT"
\t\treport_title.add_theme_font_size_override("font_size", 20)
\t\treport_box.add_child(report_title)
\t\tvar report_text: Label = Label.new()
\t\treport_text.text = last_enforcement_report
\t\treport_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\treport_box.add_child(report_text)
\t\tvar acknowledge: Button = Button.new()
\t\tacknowledge.text = "ACKNOWLEDGE REPORT"
\t\tacknowledge.custom_minimum_size.y = 48
\t\tacknowledge.pressed.connect(_acknowledge_enforcement_report)
\t\treport_box.add_child(acknowledge)

'''
    if heat_events_marker not in text:
        raise RuntimeError("Heat events UI marker not found")
    text = text.replace(heat_events_marker, heat_report_block + heat_events_marker, 1)

    heat_func_marker = "func _build_stats_app() -> void:\n"
    heat_ack_func = '''func _acknowledge_enforcement_report() -> void:
\tenforcement_report_pending = false
\t_save_game()
\t_refresh_phone()

'''
    if heat_func_marker not in text:
        raise RuntimeError("Heat report function marker not found")
    text = text.replace(heat_func_marker, heat_ack_func + heat_func_marker, 1)

    save_old = '''\t\t"raid_warning_day": raid_warning_day,
\t\t"raids_survived": raids_survived,
\t\t"last_raid_day": last_raid_day,
\t\t"raid_lockdown_until_day": raid_lockdown_until_day,
'''
    save_new = '''\t\t"raid_warning_day": raid_warning_day,
\t\t"raids_survived": raids_survived,
\t\t"last_raid_day": last_raid_day,
\t\t"raid_lockdown_until_day": raid_lockdown_until_day,
\t\t"reeves_last_payment_day": reeves_last_payment_day,
\t\t"reeves_last_missed_day": reeves_last_missed_day,
\t\t"enforcement_report_pending": enforcement_report_pending,
\t\t"last_enforcement_report": last_enforcement_report,
'''
    if save_old not in text:
        raise RuntimeError("Heat save marker not found")
    text = text.replace(save_old, save_new, 1)

    load_old = '''\traid_warning_day = int(data.get("raid_warning_day", raid_warning_day))
\traids_survived = maxi(0, int(data.get("raids_survived", raids_survived)))
\tlast_raid_day = int(data.get("last_raid_day", last_raid_day))
\traid_lockdown_until_day = maxi(0, int(data.get("raid_lockdown_until_day", raid_lockdown_until_day)))
'''
    load_new = '''\traid_warning_day = int(data.get("raid_warning_day", raid_warning_day))
\traids_survived = maxi(0, int(data.get("raids_survived", raids_survived)))
\tlast_raid_day = int(data.get("last_raid_day", last_raid_day))
\traid_lockdown_until_day = maxi(0, int(data.get("raid_lockdown_until_day", raid_lockdown_until_day)))
\treeves_last_payment_day = int(data.get("reeves_last_payment_day", reeves_last_payment_day))
\treeves_last_missed_day = int(data.get("reeves_last_missed_day", reeves_last_missed_day))
\tenforcement_report_pending = bool(data.get("enforcement_report_pending", enforcement_report_pending))
\tlast_enforcement_report = str(data.get("last_enforcement_report", last_enforcement_report))
'''
    if load_old not in text:
        raise RuntimeError("Heat load marker not found")
    text = text.replace(load_old, load_new, 1)

    # Reeves $8,000 protection-balance model + Lay Low integration.
    obligation_const = "const REEVES_FINAL_PAYOFF_BASE: int = 10000\n"
    if obligation_const not in text:
        raise RuntimeError("Reeves obligation constant marker not found")
    text = text.replace(
        obligation_const,
        obligation_const + "const REEVES_TOTAL_OBLIGATION: int = 8000\n",
        1,
    )

    old_advancement = '{"id": "reeves_negotiate", "category": "Heat", "tier": 4, "title": "Play Hardball", "description": "Successfully negotiate better terms with Reeves.", "metric": "reeves_negotiations", "target": 1, "reward_cash": 0, "reward_xp": 180, "reward_rep": 5},'
    new_advancement = """{"id": "reeves_negotiate", "category": "Heat", "tier": 4, "title": "Settle Up", "description": "Clear Reeves's remaining protection balance in one payment.", "metric": "reeves_negotiations", "target": 1, "reward_cash": 0, "reward_xp": 180, "reward_rep": 5},"""
    if old_advancement not in text:
        raise RuntimeError("Reeves advancement marker not found")
    text = text.replace(old_advancement, new_advancement, 1)

    payment_helpers_old = '''func _reeves_payment_amount() -> int:
\treturn REEVES_BASE_PAYMENT + reeves_payment_level * 300 + maxi(0, grower_level - 5) * 55

func _reeves_final_payoff_cost() -> int:
\treturn REEVES_FINAL_PAYOFF_BASE + reeves_payment_level * 2500
'''
    payment_helpers_new = '''func _reeves_remaining_balance() -> int:
\treturn maxi(0, REEVES_TOTAL_OBLIGATION - reeves_total_paid)

func _reeves_half_payment_amount() -> int:
\tvar remaining: int = _reeves_remaining_balance()
\tif remaining <= 0 or cash <= 0:
\t\treturn 0
\treturn mini(remaining, maxi(1, int(floor(float(cash) * 0.50))))

func _reeves_payment_amount() -> int:
\treturn _reeves_half_payment_amount()

func _reeves_final_payoff_cost() -> int:
\treturn _reeves_remaining_balance()
'''
    if payment_helpers_old not in text:
        raise RuntimeError("Reeves payment helper marker not found")
    text = text.replace(payment_helpers_old, payment_helpers_new, 1)

    text = text.replace(
        'return reeves_arrangement_active and reeves_next_payment_day > 0 and game_day >= reeves_next_payment_day',
        'return reeves_arrangement_active and _reeves_remaining_balance() > 0 and reeves_next_payment_day > 0 and game_day >= reeves_next_payment_day',
        1,
    )

    visit_pattern = r'func _open_reeves_visit\(\) -> void:\n.*?(?=func _reeves_primary_action\(\) -> void:\n)'
    visit_new = '''func _open_reeves_visit() -> void:
\tif customer_patience_timer != null:
\t\tcustomer_patience_timer.stop()
\tcustomer_answered = true
\tknock_banner.visible = false
\tsale_panel.visible = true
\tif sale_customer_art != null:
\t\tsale_customer_art.visible = false
\t_clear_substitutes()
\tif not reeves_met:
\t\treeves_met = true
\t\t_increment_advancement_stat("reeves_meetings")
\t\tcorrupt_contact_unlocked = true
\tvar remaining: int = _reeves_remaining_balance()
\tvar half_now: int = _reeves_half_payment_amount()
\tif not reeves_arrangement_active:
\t\tsale_title.text = "AGENT REEVES - FIRST ENCOUNTER"
\t\tsale_body.text = "\\"You are getting noticed. My number is $%d total.\\"\\n\\nPAY HALF puts 50%% of your current cash toward the balance. PAY FULL clears the entire remaining balance. REFUSE keeps your money, but Heat and enforcement risk stay on you. You can use Phone > Heat > LAY LOW to shut the operation down and hide out." % REEVES_TOTAL_OBLIGATION
\telse:
\t\tsale_title.text = "AGENT REEVES - PAYMENT DUE"
\t\tsale_body.text = "\\"Time to keep your end.\\"\\n\\nProtection balance: $%d / $%d remaining\\nPay half now: $%d\\nCurrent enforcement risk: %d%%\\nMissed payments: %d\\n\\nYou can REFUSE and then LAY LOW, but protection is suspended while the payment is missed." % [remaining, REEVES_TOTAL_OBLIGATION, half_now, int(round(enforcement_risk)), reeves_missed_payments]
\t_set_sale_action_labels("PAY HALF $%d" % half_now, "PAY FULL $%d" % remaining, "REFUSE")
\t_save_game()

'''
    text, count = re.subn(visit_pattern, visit_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Reeves visit function replacement failed")

    primary_pattern = r'func _reeves_primary_action\(\) -> void:\n.*?(?=func _reeves_secondary_action\(\) -> void:\n)'
    primary_new = '''func _reeves_primary_action() -> void:
\t_reeves_pay_half(false)

'''
    text, count = re.subn(primary_pattern, primary_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Reeves primary action replacement failed")

    secondary_pattern = r'func _reeves_secondary_action\(\) -> void:\n.*?(?=func _reeves_decline_action\(\) -> void:\n)'
    secondary_new = '''func _reeves_secondary_action() -> void:
\t_reeves_pay_full(false)

'''
    text, count = re.subn(secondary_pattern, secondary_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Reeves secondary action replacement failed")

    decline_pattern = r'func _reeves_decline_action\(\) -> void:\n.*?(?=func _start_reeves_arrangement\(negotiated: bool\) -> void:\n)'
    decline_new = '''func _reeves_decline_action() -> void:
\tif reeves_visit_reason == "first_offer" or not reeves_arrangement_active:
\t\tenforcement_risk = clampf(enforcement_risk + 20.0, 0.0, 100.0)
\t\treeves_next_payment_day = game_day + 2
\t\t_add_heat(5.0, "Reeves arrangement refused", false)
\t\traid_warning_day = game_day if enforcement_risk >= RAID_RISK_WARNING_THRESHOLD else raid_warning_day
\t\t_log_heat_event("You refused Reeves. Enforcement risk increased. Laying low can cool the operation down.")
\t\tstatus_label.text = "You refused Reeves. Use Phone > Heat > LAY LOW if you want to shut down, turn the lights down, and hide out."
\t\t_end_reeves_visit()
\telse:
\t\t_miss_reeves_payment()

'''
    text, count = re.subn(decline_pattern, decline_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Reeves decline action replacement failed")

    payment_functions_pattern = r'func _start_reeves_arrangement\(negotiated: bool\) -> void:\n.*?(?=func _miss_reeves_payment\(\) -> void:\n)'
    payment_functions_new = '''func _reeves_apply_payment(amount: int, full_payment: bool, early: bool) -> void:
\tvar remaining_before: int = _reeves_remaining_balance()
\tif remaining_before <= 0:
\t\tif reeves_arrangement_active:
\t\t\t_end_reeves_arrangement("balance already settled")
\t\treturn
\tif early and reeves_last_payment_day == game_day:
\t\tstatus_label.text = "You already paid Reeves today."
\t\treturn
\tamount = mini(amount, remaining_before)
\tif amount <= 0:
\t\tstatus_label.text = "You do not have cash available for a Reeves payment. Refuse or lay low."
\t\treturn
\tif cash < amount:
\t\tstatus_label.text = "You need $%d for that Reeves payment." % amount
\t\treturn
\tvar first_payment: bool = not reeves_arrangement_active
\tcash -= amount
\t_record_daily_expense("Reeves protection payment", amount)
\treeves_total_paid = mini(REEVES_TOTAL_OBLIGATION, reeves_total_paid + amount)
\treeves_last_payment_day = game_day
\treeves_last_missed_day = -1
\treeves_missed_payments = 0
\treeves_arrangement_active = true
\treeves_arrangement_ended = false
\treeves_relationship = mini(100, maxi(25, reeves_relationship) + (8 if full_payment else 4))
\tenforcement_risk = maxf(0.0, enforcement_risk - (20.0 if full_payment else 12.0))
\t_increment_advancement_stat("reeves_payments")
\tif first_payment:
\t\t_increment_advancement_stat("reeves_arrangements")
\t\t_reduce_heat(REEVES_INITIAL_HEAT_REDUCTION, "Reeves arrangement started", true)
\t_update_cash_ui()
\tvar remaining_after: int = _reeves_remaining_balance()
\tif remaining_after <= 0:
\t\tif full_payment:
\t\t\t_increment_advancement_stat("reeves_negotiations")
\t\tstatus_label.text = "Reeves is paid in full. The $%d protection balance is settled." % REEVES_TOTAL_OBLIGATION
\t\t_end_reeves_arrangement("protection balance paid")
\t\tif sale_panel != null and sale_panel.visible and str(current_customer.get("special", "")) == "reeves":
\t\t\t_end_reeves_visit()
\t\treturn
\treeves_next_payment_day = maxi(game_day, reeves_next_payment_day) + REEVES_PAYMENT_INTERVAL_DAYS if early and reeves_next_payment_day > game_day else game_day + REEVES_PAYMENT_INTERVAL_DAYS
\tstatus_label.text = "Paid Reeves $%d. $%d remains. Next payment: Day %d." % [amount, remaining_after, reeves_next_payment_day]
\tif sale_panel != null and sale_panel.visible and str(current_customer.get("special", "")) == "reeves":
\t\t_end_reeves_visit()
\telse:
\t\t_save_game()
\t\t_refresh_phone()

func _reeves_pay_half(early: bool = false) -> void:
\t_reeves_apply_payment(_reeves_half_payment_amount(), false, early)

func _reeves_pay_full(early: bool = false) -> void:
\tvar remaining: int = _reeves_remaining_balance()
\tif remaining <= 0:
\t\tstatus_label.text = "Reeves's $%d protection balance is already settled." % REEVES_TOTAL_OBLIGATION
\t\treturn
\tif cash < remaining:
\t\tstatus_label.text = "You need $%d to clear Reeves's remaining balance." % remaining
\t\treturn
\t_reeves_apply_payment(remaining, true, early)

func _start_reeves_arrangement(negotiated: bool) -> void:
\t_reeves_pay_half(false)

func _pay_reeves_due(early: bool = false) -> void:
\t_reeves_pay_half(early)

'''
    text, count = re.subn(payment_functions_pattern, payment_functions_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Reeves payment functions replacement failed")

    text = text.replace(
        'status_label.text = "Reeves payment missed. Enforcement risk: %d%%." % int(round(enforcement_risk))',
        'status_label.text = "Reeves payment refused. Enforcement risk: %d%%. LAY LOW is available in Phone > Heat." % int(round(enforcement_risk))',
        1,
    )

    lay_low_old = '''func _start_lay_low() -> void:
\tlay_low_active = true
\tif business_open:
\t\t_set_business_away()
\tstatus_label.text = "You are laying low. Listings are paused and Heat will cool much faster while AFewBuds stays quiet."
\t_save_game()
\t_refresh_phone()
'''
    lay_low_new = '''func _start_lay_low() -> void:
\tlay_low_active = true
\tif business_open:
\t\t_set_business_away()
\tmain_ceiling_light_on = false
\tfloor_lamp_on = false
\tgrow_room_light_on = false
\tgrow_lights_on = false
\t_refresh_light_interaction_visuals()
\t_update_day_night_visuals()
\tstatus_label.text = "LAY LOW active. Storefront closed, customer/dealer traffic stopped, and lights are down. Heat will cool much faster while you hide out."
\t_save_game()
\t_refresh_phone()
'''
    if lay_low_old not in text:
        raise RuntimeError("Lay Low function marker not found")
    text = text.replace(lay_low_old, lay_low_new, 1)

    text = text.replace(
        'lay_low.text = "REOPEN AFewBuds" if lay_low_active else "LAY LOW • CLOSE STOREFRONT"',
        'lay_low.text = "REOPEN AFewBuds" if lay_low_active else "LAY LOW - CLOSE + LIGHTS DOWN"',
        1,
    )

    reeves_card_pattern = r'\tif reeves_met or reeves_arrangement_active:\n.*?(?=\tif OS\.is_debug_build\(\) and not reeves_met:\n)'
    reeves_card_new = '''\tif reeves_met or reeves_arrangement_active:
\t\tvar reeves_card: PanelContainer = PanelContainer.new()
\t\treeves_card.add_theme_stylebox_override("panel", _style_box(Color("17191d"), Color("8d6e56"), 16, 1))
\t\tphone_list.add_child(reeves_card)
\t\tvar reeves_box: VBoxContainer = VBoxContainer.new()
\t\treeves_box.add_theme_constant_override("separation", 7)
\t\treeves_card.add_child(reeves_box)
\t\tvar reeves_title: Label = Label.new()
\t\treeves_title.text = "AGENT REEVES - %s" % ("ACTIVE BALANCE" if reeves_arrangement_active else ("SETTLED" if reeves_arrangement_ended else "NO ARRANGEMENT"))
\t\treeves_title.add_theme_font_size_override("font_size", 20)
\t\treeves_box.add_child(reeves_title)
\t\tvar remaining: int = _reeves_remaining_balance()
\t\tvar half_now: int = _reeves_half_payment_amount()
\t\tvar reeves_info: Label = Label.new()
\t\treeves_info.text = "Relationship: %d / 100\\nEnforcement risk: %d%%\\nMissed/refused payments: %d\\nProtection paid: $%d / $%d\\nRemaining balance: $%d%s" % [reeves_relationship, int(round(enforcement_risk)), reeves_missed_payments, mini(reeves_total_paid, REEVES_TOTAL_OBLIGATION), REEVES_TOTAL_OBLIGATION, remaining, ("\\nNext Reeves visit: Day %d" % reeves_next_payment_day) if reeves_arrangement_active and remaining > 0 else ""]
\t\treeves_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\treeves_box.add_child(reeves_info)
\t\tif reeves_arrangement_active and remaining > 0:
\t\t\tvar pay_half: Button = Button.new()
\t\t\tpay_half.text = "PAY HALF EARLY - $%d" % half_now
\t\t\tpay_half.disabled = half_now <= 0
\t\t\tpay_half.custom_minimum_size.y = 50
\t\t\tpay_half.pressed.connect(_reeves_pay_half.bind(true))
\t\t\treeves_box.add_child(pay_half)
\t\t\tvar pay_full: Button = Button.new()
\t\t\tpay_full.text = "PAY FULL BALANCE - $%d" % remaining
\t\t\tpay_full.disabled = cash < remaining
\t\t\tpay_full.custom_minimum_size.y = 50
\t\t\tpay_full.pressed.connect(_reeves_pay_full.bind(true))
\t\t\treeves_box.add_child(pay_full)
\t\t\tvar quiet_exit: Button = Button.new()
\t\t\tquiet_exit.text = "END ARRANGEMENT - GO QUIET (%d/%d DAYS)" % [reeves_quiet_days, REEVES_QUIET_EXIT_DAYS]
\t\t\tquiet_exit.disabled = business_open or heat > 10.0 or reeves_quiet_days < REEVES_QUIET_EXIT_DAYS
\t\t\tquiet_exit.custom_minimum_size.y = 50
\t\t\tquiet_exit.pressed.connect(_reeves_quiet_exit)
\t\t\treeves_box.add_child(quiet_exit)
\t\tvar legal_note: Label = Label.new()
\t\tlegal_note.text = "REFUSE at the door if you want to keep your cash. Then use LAY LOW above to close the operation and cool pressure. Paying the full $8,000 balance settles Reeves completely."
\t\tlegal_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
\t\tlegal_note.modulate = Color("aeb9bf")
\t\treeves_box.add_child(legal_note)

'''
    text, count = re.subn(reeves_card_pattern, reeves_card_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Reeves Heat card replacement failed")

    final_payoff_pattern = r'func _reeves_final_payoff\(\) -> void:\n.*?(?=func _reeves_quiet_exit\(\) -> void:\n)'
    final_payoff_new = '''func _reeves_final_payoff() -> void:
\t_reeves_pay_full(true)

'''
    text, count = re.subn(final_payoff_pattern, final_payoff_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Reeves final payoff replacement failed")

    # Existing careers that already paid at least $8,000 under the old recurring model
    # are treated as settled instead of asking them to pay again.
    migration_marker = '\treeves_total_paid = maxi(0, int(data.get("reeves_total_paid", reeves_total_paid)))\n'
    migration_new = '''\treeves_total_paid = clampi(int(data.get("reeves_total_paid", reeves_total_paid)), 0, REEVES_TOTAL_OBLIGATION)
\tif reeves_total_paid >= REEVES_TOTAL_OBLIGATION:
\t\treeves_arrangement_active = false
\t\treeves_arrangement_ended = true
\t\treeves_next_payment_day = 0
\t\treeves_missed_payments = 0
'''
    if migration_marker not in text:
        raise RuntimeError("Reeves old-save migration marker not found")
    text = text.replace(migration_marker, migration_new, 1)

    # Malik production-worker 3D v1 + genetics recipe progression.
    worker_var_old = "var production_worker_face_shell: MeshInstance3D\n"
    if worker_var_old not in text:
        raise RuntimeError("Production worker variable marker not found")
    text = text.replace(
        worker_var_old,
        worker_var_old + "var production_worker_malik_details: Node3D\n",
        1,
    )

    worker_build_old = '''\tproduction_worker_node.add_child(production_worker_task_label)

\t_refresh_production_worker_friend_face()
'''
    worker_build_new = '''\tproduction_worker_node.add_child(production_worker_task_label)

\t_build_malik_production_model_details()
\t_refresh_production_worker_friend_face()
'''
    if worker_build_old not in text:
        raise RuntimeError("Production worker build marker not found")
    text = text.replace(worker_build_old, worker_build_new, 1)

    worker_face_marker = "func _worker_face_texture_path(friend_name: String) -> String:\n"
    malik_model_block = '''func _malik_detail_box(parent: Node3D, detail_name: String, size: Vector3, position_value: Vector3, color_value: Color, rotation_value: Vector3 = Vector3.ZERO) -> MeshInstance3D:
\tvar part: MeshInstance3D = MeshInstance3D.new()
\tpart.name = detail_name
\tvar mesh: BoxMesh = BoxMesh.new()
\tmesh.size = size
\tmesh.material = _make_flat_material(color_value, 0.84)
\tpart.mesh = mesh
\tpart.position = position_value
\tpart.rotation = rotation_value
\tparent.add_child(part)
\treturn part

func _malik_detail_cylinder(parent: Node3D, detail_name: String, radius_value: float, height_value: float, position_value: Vector3, color_value: Color, rotation_value: Vector3 = Vector3.ZERO) -> MeshInstance3D:
\tvar part: MeshInstance3D = MeshInstance3D.new()
\tpart.name = detail_name
\tvar mesh: CylinderMesh = CylinderMesh.new()
\tmesh.top_radius = radius_value
\tmesh.bottom_radius = radius_value
\tmesh.height = height_value
\tmesh.radial_segments = 10
\tmesh.material = _make_flat_material(color_value, 0.82)
\tpart.mesh = mesh
\tpart.position = position_value
\tpart.rotation = rotation_value
\tparent.add_child(part)
\treturn part

func _build_malik_production_model_details() -> void:
\tif production_worker_node == null:
\t\treturn
\tproduction_worker_malik_details = Node3D.new()
\tproduction_worker_malik_details.name = "MalikModelV1"
\tproduction_worker_malik_details.visible = false
\tproduction_worker_node.add_child(production_worker_malik_details)

\tvar cloth: Color = Color("111315")
\tvar cloth_detail: Color = Color("1b1e21")
\tvar skin: Color = Color("b57955")
\tvar ink: Color = Color("352a28")
\tvar hair: Color = Color("171513")
\tvar sole: Color = Color("e4e5e3")
\tvar shoe: Color = Color("15181c")
\tvar accent: Color = Color("b84d4d")

\t# Polo collar / placket.
\t_malik_detail_box(production_worker_malik_details, "PoloCollarL", Vector3(0.12, 0.035, 0.16), Vector3(-0.065, 1.49, -0.185), cloth_detail, Vector3(0, 0, deg_to_rad(-18.0)))
\t_malik_detail_box(production_worker_malik_details, "PoloCollarR", Vector3(0.12, 0.035, 0.16), Vector3(0.065, 1.49, -0.185), cloth_detail, Vector3(0, 0, deg_to_rad(18.0)))
\t_malik_detail_box(production_worker_malik_details, "PoloPlacket", Vector3(0.045, 0.16, 0.025), Vector3(0, 1.405, -0.224), Color("181a1d"))

\t# Cargo-pocket silhouette on both thighs.
\t_malik_detail_box(production_worker_malik_details, "CargoPocketL", Vector3(0.15, 0.20, 0.055), Vector3(-0.19, 0.68, -0.035), cloth_detail)
\t_malik_detail_box(production_worker_malik_details, "CargoPocketR", Vector3(0.15, 0.20, 0.055), Vector3(0.19, 0.68, -0.035), cloth_detail)

\t# Sneaker soles, side panels and small red tongue accents.
\tfor side_index in range(2):
\t\tvar side: float = -1.0 if side_index == 0 else 1.0
\t\t_malik_detail_box(production_worker_malik_details, "Sole%d" % side_index, Vector3(0.20, 0.045, 0.35), Vector3(0.11 * side, 0.075, -0.07), sole)
\t\t_malik_detail_box(production_worker_malik_details, "ShoePanel%d" % side_index, Vector3(0.11, 0.045, 0.19), Vector3(0.11 * side, 0.135, -0.145), Color("d5d7d6"))
\t\t_malik_detail_box(production_worker_malik_details, "ShoeAccent%d" % side_index, Vector3(0.035, 0.055, 0.025), Vector3(0.11 * side, 0.19, -0.10), accent)

\t# Braids run over the scalp and trail slightly behind the head.
\tfor braid_index in range(7):
\t\tvar x_offset: float = (float(braid_index) - 3.0) * 0.037
\t\t_malik_detail_cylinder(production_worker_malik_details, "Braid%d" % braid_index, 0.0105, 0.30, Vector3(x_offset, 1.84, 0.045), hair, Vector3(deg_to_rad(72.0), 0, 0))
\tfor tail_index in range(4):
\t\tvar tail_x: float = (float(tail_index) - 1.5) * 0.045
\t\t_malik_detail_cylinder(production_worker_malik_details, "BraidTail%d" % tail_index, 0.011, 0.19, Vector3(tail_x, 1.70, 0.17), hair, Vector3(deg_to_rad(18.0), 0, 0))

\t# Beard / jaw silhouette. Face texture still supplies the detailed likeness.
\t_malik_detail_box(production_worker_malik_details, "BeardChin", Vector3(0.17, 0.07, 0.035), Vector3(0, 1.575, -0.188), hair)
\t_malik_detail_box(production_worker_malik_details, "BeardL", Vector3(0.065, 0.16, 0.025), Vector3(-0.13, 1.635, -0.16), hair, Vector3(0, 0, deg_to_rad(-18.0)))
\t_malik_detail_box(production_worker_malik_details, "BeardR", Vector3(0.065, 0.16, 0.025), Vector3(0.13, 1.635, -0.16), hair, Vector3(0, 0, deg_to_rad(18.0)))

\t# Tattoo bands/marks on both forearms, visible at normal gameplay distance.
\tfor side_index in range(2):
\t\tvar side: float = -1.0 if side_index == 0 else 1.0
\t\tfor band_index in range(3):
\t\t\t_malik_detail_cylinder(production_worker_malik_details, "Tattoo%d_%d" % [side_index, band_index], 0.071, 0.025, Vector3(0.28 * side, 1.02 - float(band_index) * 0.085, -0.003), ink)

func _apply_production_worker_character_style(friend_name: String) -> void:
\tif production_worker_node == null:
\t\treturn
\tvar malik_active: bool = friend_name == "Malik"
\tif production_worker_malik_details != null:
\t\tproduction_worker_malik_details.visible = malik_active
\tvar torso: MeshInstance3D = production_worker_node.get_node_or_null("Torso") as MeshInstance3D
\tvar arm_l: MeshInstance3D = production_worker_node.get_node_or_null("ArmL") as MeshInstance3D
\tvar arm_r: MeshInstance3D = production_worker_node.get_node_or_null("ArmR") as MeshInstance3D
\tvar leg_l: MeshInstance3D = production_worker_node.get_node_or_null("LegL") as MeshInstance3D
\tvar leg_r: MeshInstance3D = production_worker_node.get_node_or_null("LegR") as MeshInstance3D
\tvar shoe_l: MeshInstance3D = production_worker_node.get_node_or_null("ShoeL") as MeshInstance3D
\tvar shoe_r: MeshInstance3D = production_worker_node.get_node_or_null("ShoeR") as MeshInstance3D
\tif malik_active:
\t\tvar black_shirt: StandardMaterial3D = _make_flat_material(Color("111315"), 0.86)
\t\tvar black_pants: StandardMaterial3D = _make_flat_material(Color("171a1e"), 0.88)
\t\tvar black_shoes: StandardMaterial3D = _make_flat_material(Color("101317"), 0.88)
\t\tif torso != null:
\t\t\ttorso.material_override = black_shirt
\t\t\ttorso.scale = Vector3(1.18, 1.03, 1.10)
\t\tfor arm in [arm_l, arm_r]:
\t\t\tif arm != null:
\t\t\t\tarm.material_override = black_shirt
\t\t\t\tarm.scale = Vector3(1.12, 1.03, 1.12)
\t\tfor leg in [leg_l, leg_r]:
\t\t\tif leg != null:
\t\t\t\tleg.material_override = black_pants
\t\t\t\tleg.scale = Vector3(1.08, 1.02, 1.08)
\t\tfor shoe_node in [shoe_l, shoe_r]:
\t\t\tif shoe_node != null:
\t\t\t\tshoe_node.material_override = black_shoes
\telse:
\t\tif torso != null:
\t\t\ttorso.material_override = null
\t\t\ttorso.scale = Vector3.ONE
\t\tfor arm in [arm_l, arm_r]:
\t\t\tif arm != null:
\t\t\t\tarm.material_override = null
\t\t\t\tarm.scale = Vector3.ONE
\t\tfor leg in [leg_l, leg_r]:
\t\t\tif leg != null:
\t\t\t\tleg.material_override = null
\t\t\t\tleg.scale = Vector3.ONE
\t\tfor shoe_node in [shoe_l, shoe_r]:
\t\t\tif shoe_node != null:
\t\t\t\tshoe_node.material_override = null

'''
    if worker_face_marker not in text:
        raise RuntimeError("Worker face function marker not found")
    text = text.replace(worker_face_marker, malik_model_block + worker_face_marker, 1)

    refresh_style_old = '''\tvar assigned_name: String = production_worker_friend_name
\tvar previous_name: String = str(production_worker_face_shell.get_meta("friend_name", "__uninitialized__"))
\tif previous_name == assigned_name:
\t\treturn
'''
    refresh_style_new = '''\tvar assigned_name: String = production_worker_friend_name
\tvar previous_name: String = str(production_worker_face_shell.get_meta("friend_name", "__uninitialized__"))
\t_apply_production_worker_character_style(assigned_name)
\tif previous_name == assigned_name:
\t\treturn
'''
    if refresh_style_old not in text:
        raise RuntimeError("Worker face refresh marker not found")
    text = text.replace(refresh_style_old, refresh_style_new, 1)

    # New fictional crossbreed strains are recipe-only and hidden from the normal seed shop.
    seed_order_old = 'const SEED_ORDER: Array[String] = ["Street Green", "Purple Dream", "Citrus Rush", "Blue Frost", "Velvet Haze", "Frozen Purple", "Golden Ember", "Cherry Glow", "Neon Berry", "Moon Cake", "Midnight Crown", "Black Cherry", "Aurora Reserve", "Solar Frost"]'
    seed_order_new = 'const SEED_ORDER: Array[String] = ["Street Green", "Purple Dream", "Citrus Rush", "Blue Frost", "Velvet Haze", "Frozen Purple", "Golden Ember", "Cherry Glow", "Neon Berry", "Moon Cake", "Midnight Crown", "Black Cherry", "Aurora Reserve", "Solar Frost", "Citrus Velvet", "Cherry Frost", "Ember Berry", "Crown Cake"]'
    if seed_order_old not in text:
        raise RuntimeError("Seed order marker not found")
    text = text.replace(seed_order_old, seed_order_new, 1)

    seed_inventory_marker = '''\t"Aurora Reserve": 0
}
'''
    seed_inventory_new = '''\t"Aurora Reserve": 0,
\t"Citrus Velvet": 0,
\t"Cherry Frost": 0,
\t"Ember Berry": 0,
\t"Crown Cake": 0
}
'''
    if seed_inventory_marker not in text:
        raise RuntimeError("Seed inventory marker not found")
    text = text.replace(seed_inventory_marker, seed_inventory_new, 1)

    seed_catalog_marker = '''\t"Solar Frost": {"unlock": 14, "cost": 210, "price": 70, "grade": "S+", "profile": "solar", "harvest": 5, "description": "Late-career prestige genetics intended for reserve-level customers."}
}
'''
    seed_catalog_new = '''\t"Solar Frost": {"unlock": 14, "cost": 210, "price": 70, "grade": "S+", "profile": "solar", "harvest": 5, "description": "Late-career prestige genetics intended for reserve-level customers."},
\t"Citrus Velvet": {"unlock": 99, "cost": 0, "price": 34, "grade": "S", "profile": "citrus", "harvest": 8, "recipe_only": true, "description": "A fictional crossbreed unlocked through Story rewards."},
\t"Cherry Frost": {"unlock": 99, "cost": 0, "price": 46, "grade": "S+", "profile": "cherry", "harvest": 6, "recipe_only": true, "description": "A fictional cold-fruit crossbreed unlocked through progression."},
\t"Ember Berry": {"unlock": 99, "cost": 0, "price": 54, "grade": "S+", "profile": "berry", "harvest": 6, "recipe_only": true, "description": "A fictional gold-and-berry crossbreed unlocked through progression."},
\t"Crown Cake": {"unlock": 99, "cost": 0, "price": 63, "grade": "S+", "profile": "luxury", "harvest": 5, "recipe_only": true, "description": "A fictional prestige crossbreed reserved for late-career genetics work."}
}
'''
    if seed_catalog_marker not in text:
        raise RuntimeError("Seed catalog marker not found")
    text = text.replace(seed_catalog_marker, seed_catalog_new, 1)

    advancement_genetics_marker = '''\t{"id": "three_hybrids", "category": "Genetics", "tier": 4, "title": "Breeding Program", "description": "Create 3 hybrid seed batches.", "metric": "hybrids_created", "target": 3, "reward_cash": 100, "reward_xp": 250, "reward_rep": 15},
'''
    advancement_genetics_new = advancement_genetics_marker + '''\t{"id": "recipe_citrus_velvet", "category": "Genetics", "tier": 2, "title": "Flavor Notes", "description": "Complete a hybrid batch and build a five-variety seed shelf.", "metric": "hybrids_created", "target": 1, "reward_cash": 0, "reward_xp": 90, "reward_rep": 5, "reward_recipe": "Citrus Velvet", "requires": [{"state": "seed_varieties", "target": 5, "label": "Seed varieties"}]},
\t{"id": "recipe_cherry_frost", "category": "Genetics", "tier": 3, "title": "Cold & Sweet", "description": "Create 3 hybrid batches and reach Grower Level 7.", "metric": "hybrids_created", "target": 3, "reward_cash": 0, "reward_xp": 150, "reward_rep": 8, "reward_recipe": "Cherry Frost", "requires": [{"state": "grower_level", "target": 7, "label": "Grower Level"}]},
\t{"id": "recipe_ember_berry", "category": "Genetics", "tier": 3, "title": "Color Theory", "description": "Create 5 hybrid batches and reach Grower Level 9.", "metric": "hybrids_created", "target": 5, "reward_cash": 0, "reward_xp": 200, "reward_rep": 10, "reward_recipe": "Ember Berry", "requires": [{"state": "grower_level", "target": 9, "label": "Grower Level"}]},
\t{"id": "recipe_crown_cake", "category": "Genetics", "tier": 4, "title": "Crown Lab", "description": "Create 8 hybrid batches, reach Grower Level 11, and complete 50 harvests.", "metric": "hybrids_created", "target": 8, "reward_cash": 0, "reward_xp": 300, "reward_rep": 15, "reward_recipe": "Crown Cake", "requires": [{"state": "grower_level", "target": 11, "label": "Grower Level"}, {"metric": "harvests", "target": 50, "label": "Harvests"}]},
'''
    if advancement_genetics_marker not in text:
        raise RuntimeError("Genetics advancement marker not found")
    text = text.replace(advancement_genetics_marker, advancement_genetics_new, 1)

    reward_text_old = '''\tvar reward_seed: String = str(entry.get("reward_seed", ""))
\tvar reward_seed_count: int = int(entry.get("reward_seed_count", 0))
'''
    reward_text_new = '''\tvar reward_seed: String = str(entry.get("reward_seed", ""))
\tvar reward_seed_count: int = int(entry.get("reward_seed_count", 0))
\tvar reward_recipe: String = str(entry.get("reward_recipe", ""))
'''
    if reward_text_old not in text:
        raise RuntimeError("Advancement reward text variable marker not found")
    text = text.replace(reward_text_old, reward_text_new, 1)
    reward_return_old = '''\tif not reward_seed.is_empty() and reward_seed_count > 0:
\t\tparts.append("%dx %s seed" % [reward_seed_count, reward_seed])
\treturn "  |  ".join(parts)
'''
    # The portable-glyph pass runs later, so base source still uses the bullet separator here.
    if reward_return_old not in text:
        reward_return_old = '''\tif not reward_seed.is_empty() and reward_seed_count > 0:
\t\tparts.append("%dx %s seed" % [reward_seed_count, reward_seed])
\treturn "  •  ".join(parts)
'''
    reward_return_new = '''\tif not reward_seed.is_empty() and reward_seed_count > 0:
\t\tparts.append("%dx %s seed" % [reward_seed_count, reward_seed])
\tif not reward_recipe.is_empty():
\t\tparts.append("GENETICS RECIPE: %s" % reward_recipe)
\treturn "  •  ".join(parts)
'''
    if reward_return_old not in text:
        raise RuntimeError("Advancement reward text return marker not found")
    text = text.replace(reward_return_old, reward_return_new, 1)

    seed_shop_loop_old = '''\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tvar unlock_level: int = int(info.get("unlock", 1))
'''
    seed_shop_loop_new = '''\t\tvar info: Dictionary = seed_catalog[seed_name]
\t\tif bool(info.get("recipe_only", false)):
\t\t\tcontinue
\t\tvar unlock_level: int = int(info.get("unlock", 1))
'''
    # Replace both normal seed-shop and next-locked scans.
    if text.count(seed_shop_loop_old) < 2:
        raise RuntimeError("Seed shop loop markers not found")
    text = text.replace(seed_shop_loop_old, seed_shop_loop_new, 2)

    genetics_pattern = r'func _build_genetics_app\(\) -> void:\n.*?(?=func _max_friend_loyalty\(\) -> int:\n)'
    genetics_new = '''func _genetics_recipe_catalog() -> Array[Dictionary]:
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
\tintro.text = "Experimental game genetics. Cross fictional parent seeds to collect hybrid lines. Some recipes are earned by claiming Story / Rewards milestones."
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
    text, count = re.subn(genetics_pattern, genetics_new, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("Genetics app replacement failed")

    # Portable UI glyph pass. Keep the phone back arrow (‹), which is known-good,
    # and replace symbols that fall back to incorrect glyphs on iOS/PWA/web fonts.
    portable_glyphs = {
        "✕": "X",
        "✓": "OK",
        "○": "[ ]",
        "★": "READY",
        "⏻": "PWR",
        "●": "O",
        "×": "x",
        "›": ">",
        "→": "->",
        "•": " | ",
        "·": " - ",
        "…": "...",
        "–": "-",
        "—": "-",
    }
    for old, new in portable_glyphs.items():
        text = text.replace(old, new)

    required_fragments = [
        "const REEVES_TOTAL_OBLIGATION: int = 8000",
        "func _reeves_pay_half(early: bool = false) -> void:",
        "func _reeves_pay_full(early: bool = false) -> void:",
        'PAY HALF $%d',
        'PAY FULL $%d',
        'Use Phone > Heat > LAY LOW',
        'LAY LOW active. Storefront closed, customer/dealer traffic stopped, and lights are down.',
        'reeves_arrangement_ended = true',
        'func _claim_all_advancements() -> void:',
        'phone_button.add_theme_stylebox_override("normal"',
        'func _show_save_notification(',
        'func _build_malik_production_model_details() -> void:',
        'production_worker_malik_details.visible = malik_active',
        '"reward_recipe": "Citrus Velvet"',
        'func _genetics_recipe_catalog() -> Array[Dictionary]:',
        'LOCKED - CLAIM %s',
    ]
    for fragment in required_fragments:
        if fragment not in text:
            raise RuntimeError("Generated game source missing required fragment: " + fragment)
    if 'status_label.text = "Game saved. Cloud backup will update automatically while signed in."' in text:
        raise RuntimeError("Old manual-save text notification is still present")
    return text

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
        f'"fileSizes":{{"index-system-malikgen1.pck":{pck_size},"index.wasm":37902138}}',
        config,
        count=1,
    )
    if '"mainPack"' in config:
        config = re.sub(
            r'"mainPack":"[^"]*"',
            '"mainPack":"index-system-malikgen1.pck"',
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
    html = re.sub(r'index\.js\?v=[^"]+', 'index.js?v=malikgen1', html, count=1)
    html = re.sub(
        r'shared/afb-cloud\.js\?v=[^"]+',
        'shared/afb-cloud.js?v=malikgen1',
        html,
        count=1,
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
