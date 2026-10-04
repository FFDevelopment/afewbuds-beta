extends Node

const InventorySlot = preload("res://scripts/inventory_slot.gd")
const BACKPACK_SLOTS := 8
const BACKPACK_WEED_CAPACITY := 40
const LOCKER_SLOTS := 12
const LOCKER_WEED_CAPACITY := 120

var game: Node
var backpack_button: Button
var backpack_panel: PanelContainer
var backpack_body: VBoxContainer
var locker_panel: PanelContainer
var locker_body: VBoxContainer

func setup(game_node: Node) -> void:
	game = game_node
	_build_backpack_button()
	_build_backpack_panel()
	_build_locker_panel()
	refresh()

func is_modal_open() -> bool:
	return (backpack_panel != null and backpack_panel.visible) or (locker_panel != null and locker_panel.visible)

func weed_amount(strain_name: String) -> int:
	return maxi(0, int(game.personal_weed.get(strain_name, 0))) if game != null else 0

func backpack_total_weed() -> int:
	var total := 0
	for value in game.personal_weed.values():
		total += maxi(0, int(value))
	return total

func locker_total_weed() -> int:
	var total := 0
	for value in game.locker_weed.values():
		total += maxi(0, int(value))
	return total

func _stack_count(kind: String) -> int:
	var count := 0
	if kind == "backpack":
		if int(game.cash) > 0:
			count += 1
		for value in game.personal_weed.values():
			if int(value) > 0:
				count += 1
	else:
		if int(game.locker_cash) > 0:
			count += 1
		for value in game.locker_weed.values():
			if int(value) > 0:
				count += 1
	return count

func _has_stack(kind: String, strain_name: String) -> bool:
	return int((game.personal_weed if kind == "backpack" else game.locker_weed).get(strain_name, 0)) > 0

func _free_weed_capacity(kind: String) -> int:
	return maxi(0, (BACKPACK_WEED_CAPACITY - backpack_total_weed()) if kind == "backpack" else (LOCKER_WEED_CAPACITY - locker_total_weed()))

func _can_add_weed(kind: String, strain_name: String) -> bool:
	if _free_weed_capacity(kind) <= 0:
		return false
	if _has_stack(kind, strain_name):
		return true
	return _stack_count(kind) < (BACKPACK_SLOTS if kind == "backpack" else LOCKER_SLOTS)

func _items(kind: String) -> Array[Dictionary]:
	var out: Array[Dictionary] = []
	var money := int(game.cash) if kind == "backpack" else int(game.locker_cash)
	if money > 0:
		out.append({"type":"cash","name":"Cash","amount":money})
	var source: Dictionary = game.personal_weed if kind == "backpack" else game.locker_weed
	var names: Array[String] = []
	for k in source.keys():
		if int(source.get(k,0)) > 0:
			names.append(str(k))
	names.sort()
	for name in names:
		out.append({"type":"weed","name":name,"amount":int(source.get(name,0))})
	return out

func _style(bg: Color, border: Color, radius := 16, width := 1) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(width)
	s.set_corner_radius_all(radius)
	s.content_margin_left = 14.0
	s.content_margin_right = 14.0
	s.content_margin_top = 12.0
	s.content_margin_bottom = 12.0
	return s

func _clear(node: Node) -> void:
	for child in node.get_children():
		child.queue_free()

func _build_backpack_button() -> void:
	backpack_button = Button.new()
	backpack_button.text = "BAG"
	backpack_button.tooltip_text = "Open backpack"
	backpack_button.set_anchors_preset(Control.PRESET_BOTTOM_RIGHT)
	backpack_button.offset_left = -96
	backpack_button.offset_top = -96
	backpack_button.offset_right = -18
	backpack_button.offset_bottom = -18
	backpack_button.custom_minimum_size = Vector2(78,78)
	backpack_button.add_theme_font_size_override("font_size", 16)
	backpack_button.add_theme_stylebox_override("normal", _style(Color("18251d"),Color("72a96f"),18,2))
	backpack_button.add_theme_stylebox_override("hover", _style(Color("223426"),Color("93c58d"),18,2))
	backpack_button.pressed.connect(toggle_backpack)
	game.hud.add_child(backpack_button)

func _build_backpack_panel() -> void:
	backpack_panel = PanelContainer.new()
	backpack_panel.set_anchors_preset(Control.PRESET_CENTER_RIGHT)
	backpack_panel.offset_left = -460
	backpack_panel.offset_top = -310
	backpack_panel.offset_right = -18
	backpack_panel.offset_bottom = 310
	backpack_panel.visible = false
	backpack_panel.add_theme_stylebox_override("panel",_style(Color("0d1317"),Color("4b6655"),20,2))
	game.hud.add_child(backpack_panel)
	backpack_body = VBoxContainer.new()
	backpack_body.add_theme_constant_override("separation",10)
	backpack_panel.add_child(backpack_body)

func _build_locker_panel() -> void:
	locker_panel = PanelContainer.new()
	locker_panel.set_anchors_preset(Control.PRESET_CENTER)
	locker_panel.offset_left = -500
	locker_panel.offset_top = -330
	locker_panel.offset_right = 500
	locker_panel.offset_bottom = 330
	locker_panel.visible = false
	locker_panel.add_theme_stylebox_override("panel",_style(Color("0d1317"),Color("596770"),20,2))
	game.hud.add_child(locker_panel)
	locker_body = VBoxContainer.new()
	locker_body.add_theme_constant_override("separation",10)
	locker_panel.add_child(locker_body)

func toggle_backpack() -> void:
	if backpack_panel.visible:
		close_backpack()
		return
	if game._any_modal_open():
		return
	backpack_panel.visible = true
	game._set_world_controls_visible(false)
	refresh()

func close_backpack() -> void:
	backpack_panel.visible = false
	game._set_world_controls_visible(true)

func open_locker() -> void:
	if backpack_panel != null:
		backpack_panel.visible = false
	locker_panel.visible = true
	game._set_world_controls_visible(false)
	refresh()

func close_locker() -> void:
	locker_panel.visible = false
	game._set_world_controls_visible(true)
	if game.views.has("main_workbench"):
		game._go_to_view("main_workbench")

func _header(parent: VBoxContainer, title_text: String, close_call: Callable) -> void:
	var row := HBoxContainer.new()
	parent.add_child(row)
	var title := Label.new()
	title.text = title_text
	title.add_theme_font_size_override("font_size",24)
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(title)
	var close := Button.new()
	close.text = "X"
	close.custom_minimum_size = Vector2(52,44)
	close.pressed.connect(close_call)
	row.add_child(close)

func _add_grid(parent: VBoxContainer, kind: String, slots: int) -> void:
	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation",8)
	grid.add_theme_constant_override("v_separation",8)
	parent.add_child(grid)
	var items := _items(kind)
	for i in range(slots):
		var slot = InventorySlot.new()
		var data: Dictionary = items[i] if i < items.size() else {}
		slot.setup(self,kind,i,data)
		grid.add_child(slot)

func _source_button(parent: VBoxContainer, text_value: String, call: Callable) -> void:
	var b := Button.new()
	b.text = text_value
	b.custom_minimum_size.y = 44
	b.pressed.connect(call)
	parent.add_child(b)

func refresh() -> void:
	if backpack_panel != null and backpack_panel.visible:
		_refresh_backpack()
	if locker_panel != null and locker_panel.visible:
		_refresh_locker()

func _refresh_backpack() -> void:
	_clear(backpack_body)
	_header(backpack_body,"BACKPACK",close_backpack)
	var summary := Label.new()
	summary.text = "8 slots   |   Packaged weed %dg / %dg   |   Pocket cash $%d" % [backpack_total_weed(),BACKPACK_WEED_CAPACITY,int(game.cash)]
	summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	backpack_body.add_child(summary)
	_add_grid(backpack_body,"backpack",BACKPACK_SLOTS)
	if game.current_view == "workbench":
		var source_title := Label.new()
		source_title.text = "BAGGING STATION - take packaged weed"
		backpack_body.add_child(source_title)
		for k in game.bagged_inventory.keys():
			var name := str(k)
			var amount := int(game.bagged_inventory.get(name,0))
			if amount > 0:
				_source_button(backpack_body,"TAKE %s  |  %dg" % [name,amount],take_bagged.bind(name))
	elif game.current_view == "storage":
		var source_title := Label.new()
		source_title.text = "BUSINESS STORAGE"
		backpack_body.add_child(source_title)
		for k in game.products.keys():
			var name := str(k)
			var amount := game._available_amount(name)
			if amount > 0:
				_source_button(backpack_body,"TAKE %s  |  %dg" % [name,amount],take_storage.bind(name))
		for k in game.personal_weed.keys():
			var name := str(k)
			var amount := int(game.personal_weed.get(name,0))
			if amount > 0:
				_source_button(backpack_body,"STORE %s  |  %dg" % [name,amount],store_backpack.bind(name))

func _refresh_locker() -> void:
	_clear(locker_body)
	_header(locker_body,"PERSONAL LOCKER",close_locker)
	var summary := Label.new()
	summary.text = "Locker packaged weed %dg / %dg   |   Locker cash $%d\nDrag cash or packaged weed between the two grids." % [locker_total_weed(),LOCKER_WEED_CAPACITY,int(game.locker_cash)]
	summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	locker_body.add_child(summary)
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation",14)
	locker_body.add_child(columns)
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.add_child(left)
	var lt := Label.new()
	lt.text = "BACKPACK"
	left.add_child(lt)
	_add_grid(left,"backpack",BACKPACK_SLOTS)
	var right := VBoxContainer.new()
	right.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.add_child(right)
	var rt := Label.new()
	rt.text = "LOCKER  |  120g"
	right.add_child(rt)
	_add_grid(right,"locker",LOCKER_SLOTS)

func _inventory_drop(data: Dictionary, target_kind: String) -> void:
	var source := str(data.get("source",""))
	if source == target_kind:
		return
	var item: Dictionary = data.get("item",{}) as Dictionary
	var item_type := str(item.get("type",""))
	if item_type == "cash":
		if source == "backpack" and target_kind == "locker":
			game.locker_cash += int(game.cash)
			game.cash = 0
		elif source == "locker" and target_kind == "backpack":
			game.cash += int(game.locker_cash)
			game.locker_cash = 0
	elif item_type == "weed":
		var strain := str(item.get("name",""))
		var source_dict: Dictionary = game.personal_weed if source == "backpack" else game.locker_weed
		var target_dict: Dictionary = game.personal_weed if target_kind == "backpack" else game.locker_weed
		var have := maxi(0,int(source_dict.get(strain,0)))
		if have <= 0 or not _can_add_weed(target_kind,strain):
			return
		var moved := mini(have,_free_weed_capacity(target_kind))
		source_dict[strain] = have - moved
		if int(source_dict.get(strain,0)) <= 0:
			source_dict.erase(strain)
		target_dict[strain] = int(target_dict.get(strain,0)) + moved
	game._update_cash_ui()
	game._save_game()
	refresh()

func _move_to_backpack(strain: String, amount: int) -> int:
	if amount <= 0 or not _can_add_weed("backpack",strain):
		return 0
	var moved := mini(amount,_free_weed_capacity("backpack"))
	game.personal_weed[strain] = int(game.personal_weed.get(strain,0)) + moved
	return moved

func take_bagged(strain: String) -> void:
	var have := maxi(0,int(game.bagged_inventory.get(strain,0)))
	var moved := _move_to_backpack(strain,have)
	if moved <= 0:
		game.status_label.text = "Backpack is full."
		return
	game.bagged_inventory[strain] = have - moved
	game.status_label.text = "Moved %dg %s from the bagging station to your backpack." % [moved,strain]
	game._save_game()
	game._refresh_bagging_panel()
	refresh()

func take_storage(strain: String) -> void:
	if not game.products.has(strain):
		return
	var available := game._available_amount(strain)
	var moved := _move_to_backpack(strain,available)
	if moved <= 0:
		game.status_label.text = "Backpack is full."
		return
	var data: Dictionary = game.products[strain]
	data["stock"] = maxi(0,int(data.get("stock",0)) - moved)
	game.products[strain] = data
	game.status_label.text = "Moved %dg %s from business storage to your backpack." % [moved,strain]
	game._save_game()
	game._refresh_storage_panel()
	refresh()

func store_backpack(strain: String) -> void:
	var have := maxi(0,int(game.personal_weed.get(strain,0)))
	if have <= 0:
		return
	var free := maxi(0,game._storage_capacity() - game._total_stored_stock())
	var moved := mini(have,free)
	if moved <= 0:
		game.status_label.text = "Business storage is full."
		return
	game.personal_weed[strain] = have - moved
	if int(game.personal_weed.get(strain,0)) <= 0:
		game.personal_weed.erase(strain)
	game._ensure_product_exists(strain)
	var data: Dictionary = game.products[strain]
	data["stock"] = int(data.get("stock",0)) + moved
	game.products[strain] = data
	game.status_label.text = "Moved %dg %s from your backpack into business storage." % [moved,strain]
	game._save_game()
	game._refresh_storage_panel()
	refresh()

func consume_weed(strain: String, amount: int) -> int:
	var have := maxi(0,int(game.personal_weed.get(strain,0)))
	var used := mini(have,maxi(0,amount))
	if used > 0:
		game.personal_weed[strain] = have - used
		if int(game.personal_weed.get(strain,0)) <= 0:
			game.personal_weed.erase(strain)
		refresh()
	return used
