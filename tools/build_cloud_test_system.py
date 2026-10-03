from pathlib import Path
import struct
import hashlib
import re

BASE_PCK = Path("cloud-test/index.pck")
OUT_PCK = Path("cloud-test/index-system-heatreeves2.pck")
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
    new_advancement = '{"id": "reeves_negotiate", "category": "Heat", "tier": 4, "title": "Settle Up", "description": "Clear Reeves\\'s remaining protection balance in one payment.", "metric": "reeves_negotiations", "target": 1, "reward_cash": 0, "reward_xp": 180, "reward_rep": 5},'
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
        f'"fileSizes":{{"index-system-heatreeves2.pck":{pck_size},"index.wasm":37902138}}',
        config,
        count=1,
    )
    if '"mainPack"' in config:
        config = re.sub(
            r'"mainPack":"[^"]*"',
            '"mainPack":"index-system-heatreeves2.pck"',
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
    html = re.sub(r'index\.js\?v=[^"]+', 'index.js?v=heatreeves2', html, count=1)
    html = re.sub(
        r'shared/afb-cloud\.js\?v=[^"]+',
        'shared/afb-cloud.js?v=heatreeves2',
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
