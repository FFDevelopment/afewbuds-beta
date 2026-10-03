from pathlib import Path
import struct
import hashlib
import re

BASE_PCK = Path("cloud-test/index.pck")
OUT_PCK = Path("cloud-test/index-system-heatcomplete1.pck")
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

    heat_func_marker = "func _build_stats_app() -> void:\\n"
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
        f'"fileSizes":{{"index-system-heatcomplete1.pck":{pck_size},"index.wasm":37902138}}',
        config,
        count=1,
    )
    if '"mainPack"' in config:
        config = re.sub(
            r'"mainPack":"[^"]*"',
            '"mainPack":"index-system-heatcomplete1.pck"',
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
    html = re.sub(r'index\.js\?v=[^"]+', 'index.js?v=heatcomplete1', html, count=1)
    html = re.sub(
        r'shared/afb-cloud\.js\?v=[^"]+',
        'shared/afb-cloud.js?v=heatcomplete1',
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
