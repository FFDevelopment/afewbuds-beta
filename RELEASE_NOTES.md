AFewBuds Mobile Beta 0.16.0-mobile-beta.13 — House Rooms & Grow-Floor Fit

Verified source: FFDevelopment/afewbuds-cloud-test main @ c59a80a29205b1078394048a8ff92f847077dbe0
Source validation: https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38180132122

HOUSE FURNITURE FIX
- Use actual structural inside wall faces for all six upper house rooms (living, packing, kitchen, bathroom, bedroom, and grow). Old stored ownership and property IDs are not rewritten.
- Packing Bench III can sit flush against solid packing-room walls with only a narrow physical clearance; the finished apartment-style bench, tray, scale, jars, and trim/pack actions remain unchanged.
- Expand the basement grow floor to the real usable side and front boundaries, preserving the actual stairs, railings, circulation area, and all upstairs floor separation.
- Keep wall/door collisions, visible window blind coverage, other furniture and stair obstructions authoritative. Furniture cannot be pushed through them.
- Carry the same physical-room bounds into walk-around arrangement, saved property room registration and placement validation.

PREVIOUS VERIFIED FIXES RETAINED
- One independently hired/assigned production worker per owned property; per-property payroll, auto-plant, status and transfer handling.
- Level I equipment purchases; item-specific upgrade prices and Grower unlock requirements; tent LED lighting upgrades without losing plants.
- Apartment-style packing benches, property curbside deliveries, permanent backpack capacity upgrades and Phone Shop browsing.
- Existing saves, user accounts, career stock, property ownership, placed furniture, cloud synchronization, session fencing and update rollback remain intact.

VALIDATION
- Mobile Godot suite passed, including 44 physical-room/basement checks, 36 production staff checks, 37 shop checks, 88 property isolation checks, 85 equipment checks.
- Public source rebuild, manifest hashes, save migration, session and updater checks, and Pages deployment are additional release gates.
