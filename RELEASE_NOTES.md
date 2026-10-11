AFewBuds Mobile Beta 0.16.0-mobile-beta.8

Source: FFDevelopment/afewbuds-cloud-test @ f3e6e89d744649ea055d45ba36e7611d7a92eb79, validated on the development main branch.

- Add furniture-aware house NPC navigation between doorways, rooms, grow stations and the staircase.
- Distinguish Door Dealers from street dealers; keep per-property on-duty controls, individual sales and commission.
- Improve Door Dealer pacing at the couch and entrance; natural stand-up, walk, service, return and seating after furniture movement.
- Include the shared PropertyRegistry / ItemRegistry foundations, property-specific employee and inventory handling, and prior Chapter 4/5 story.
- Add Low / Medium / High graphics quality options under Pause > Settings, stored on each device only.
- Preserve beta.7 Reeves post-payoff contacts, protection settlement and advancement changes.
- Exclude the unfinished Mission & Story Engine draft and the unbuilt player-character creator.

Existing tester URL, home-screen PWA origin, account and session configuration, save protocol, legacy-career migration, updater manifest, service worker and cache rollback are retained. Old mobile PWAs should detect the bumped manifest on reopen and verify new assets before switching. Cloud and local careers must not be erased.

Must pass the full Godot mobile gameplay/property/employee regression suite, updater/legacy-save tests, SHA-256 manifest validation and deploy checks before any release is considered published.
