extends PanelContainer

var inventory_owner = null
var container_kind: String = ""
var slot_index: int = 0
var item_data: Dictionary = {}
var label: Label

func setup(owner_node, kind: String, index: int, data: Dictionary) -> void:
	inventory_owner = owner_node
	container_kind = kind
	slot_index = index
	item_data = data.duplicate(true)
	custom_minimum_size = Vector2(108, 86)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var style := StyleBoxFlat.new()
	style.bg_color = Color("11181d") if item_data.is_empty() else Color("19251f")
	style.border_color = Color("34434a") if item_data.is_empty() else Color("6c9a71")
	style.set_border_width_all(1)
	style.set_corner_radius_all(12)
	style.content_margin_left = 7.0
	style.content_margin_right = 7.0
	style.content_margin_top = 7.0
	style.content_margin_bottom = 7.0
	add_theme_stylebox_override("panel", style)
	label = Label.new()
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size", 14)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(label)
	_refresh_text()

func _refresh_text() -> void:
	if label == null:
		return
	if item_data.is_empty():
		label.text = "EMPTY"
		label.modulate = Color(1,1,1,0.34)
		return
	label.modulate = Color.WHITE
	var item_type := str(item_data.get("type", ""))
	if item_type == "cash":
		label.text = "CASH\n$%d" % int(item_data.get("amount", 0))
	elif item_type == "weed":
		label.text = "%s\n%dg" % [str(item_data.get("name", "Packaged Weed")), int(item_data.get("amount", 0))]
	else:
		label.text = str(item_data.get("name", "ITEM"))

func _get_drag_data(_at_position: Vector2) -> Variant:
	if item_data.is_empty() or inventory_owner == null:
		return null
	var preview := PanelContainer.new()
	preview.custom_minimum_size = Vector2(118, 66)
	var preview_style := StyleBoxFlat.new()
	preview_style.bg_color = Color("1e2c24")
	preview_style.border_color = Color("89bd83")
	preview_style.set_border_width_all(2)
	preview_style.set_corner_radius_all(12)
	preview.add_theme_stylebox_override("panel", preview_style)
	var preview_label := Label.new()
	preview_label.text = label.text if label != null else "ITEM"
	preview_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	preview_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	preview.add_child(preview_label)
	set_drag_preview(preview)
	return {"source": container_kind, "item": item_data.duplicate(true)}

func _can_drop_data(_at_position: Vector2, data: Variant) -> bool:
	if not (data is Dictionary):
		return false
	var d: Dictionary = data as Dictionary
	return d.has("source") and d.has("item") and str(d.get("source", "")) != container_kind

func _drop_data(_at_position: Vector2, data: Variant) -> void:
	if inventory_owner == null or not (data is Dictionary):
		return
	inventory_owner.call("_inventory_drop", data as Dictionary, container_kind)
