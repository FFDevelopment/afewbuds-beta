AFewBuds Mobile Beta 0.16.0-mobile-beta.9 — Landing Collision / Unstuck Hotfix

Source: FFDevelopment/afewbuds-cloud-test @ c7549547a82702c6aedb200a8726c45872990ab4, validated in the mobile branch and full main development workflow.

- Fixed missing player collision on the two closed starter-apartment side fire-escape doors (apartments 201 and 301) at the upper landings. The existing stairs, rails, doors and artwork remain in place.
- Added UNSTUCK · RETURN TO SAFE SPOT to Pause on touchscreen/mobile and controller/keyboard desktop menus.
- Recovery checks the nearest previously valid grounded position or a nearby supported public/landing anchor against the player's physical capsule. It will not teleport if no safe position is verified.
- Unstuck is cooldown-limited, resets unsafe movement velocity, and preserves the game's paused state until Resume.
- Preserves careers, money, workers, inventories, property ownership, furniture, growth, customer history, and save schema. The corrected position is written through the existing save pipeline.
- No changes to tester URL, PWA service worker, update manifest protocol, user identity, cloud login, or the public updater's rollback behavior.
- No unmerged Mission & Story Engine or future customizable-player prototypes.

The feature branch passed Godot import, movement, landing collider/raycast checks, Unstuck/cooldown/career checks, property/inventory/graphics and other mobile suites. The main development baseline was rebuilt successfully, then released through the official beta validator and SHA-256 updater manifest.
