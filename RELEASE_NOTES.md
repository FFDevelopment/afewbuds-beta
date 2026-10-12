AFewBuds Mobile Beta 0.16.0-mobile-beta.19 — Physical Customer Visits, Emergency Heat Controls & Readable Stock Buttons

VERIFIED MOBILE SOURCE
- FFDevelopment/afewbuds-cloud-test main @ 0cb4c6a98d071bfc9a209e0269d7d33189a80032
- Godot mobile movement, imported runtime, property inventory, phone, staff, heat, story/visitors, and safe save regression:
  https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38299681502

MOBILE PHONE INVENTORY
- LIST / UNLIST buttons display at full readable/tappable width on a compact phone screen. They no longer collapse into a blank vertical green strip.
- Product listing, available sellable grams, and reserved amounts aggregate all placed storage units at each property while keeping apartment and house stock independent.
- Player, dealer-door, worker, and staff sales/deposits deduct from the correct physical storage bins. Reserve stock is never sold twice.

HEAT & SHOP SAFETY
- Phone > Heat and the individual property overview offer direct owner CLOSE SHOP and SHUT DOWN & LAY LOW actions even at critical Heat or with no employees currently on duty.
- An off-duty worker can still relay CLOSE or SHUT DOWN to protect the property, but cannot reopen or return to duty during Heat/raid restrictions.
- Lay Low closes customer traffic and lowers equipment power; reopening is locked until Heat is below 75 and raid restrictions have expired. The player's existing worker assignment preferences are preserved.

FIRST PHYSICAL CUSTOMER ENCOUNTERS (APARTMENT)
- Opening the apartment front door brings the actual 3D customer into view instead of requiring the standard buyer peephole to sell.
- Use existing SELL / SUBSTITUTE / DECLINE stock and payment controls; the visiting character walks down the street and disappears away from the doorway after leaving.
- Some regulars can invite the player to a short smoke session after a sale. Accepting or declining has a real interaction; a completed visit gives a once-per-client/day loyalty reward.
- Agent Reeves keeps his separate story encounter. The legacy peephole remains as a fallback for unsupported/special scenes.
- Roaming town clients and off-site timed meetups are still future features, not part of beta.19.

SAVE SAFETY / RELEASE GATE
- Existing account, player saves, crops, production-worker assignments, storage containers, property inventory, money and equipment placements are retained.
- Never replace the existing public game pack without rebuilt and independently validated mobile artifacts, SHA-256 updater manifest, session and old-save migration checks, and successful Pages deploy.
