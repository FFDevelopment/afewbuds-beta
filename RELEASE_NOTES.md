AFewBuds Mobile Beta 0.16.0-mobile-beta.17 — Production Duty & Wall-Mounted Equipment Hotfix

VERIFIED MOBILE SOURCE
- FFDevelopment/afewbuds-cloud-test main @ 71cf1f0c1dad422415661d6efe14c94b902e80a8
- Full mobile gameplay, interaction and map regression suite: https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38201336519
- Both production duty and mounted equipment regressions passed in the same verified export.

PRODUCTION WORKERS & DAY CLOSEOUT
- Workers temporarily suspended because nightly wages could not be paid now retain their prior on-duty preference and resume automatically when sufficient cash arrives, including after settling the dealer drop-off, and only after the actual overdue wages are paid.
- Preserves manual time-off choices. Workers never work for free. Arrest, bail, heat or raid restrictions still apply.
- Both independent house and apartment production workers, shifts, automation settings and payroll remain separate.

WALL-MOUNTED EQUIPMENT — MOBILE WALK-AROUND FURNITURE ARRANGEMENT
- Look directly at an installed auto-waterer or ventilation unit to select it, move it or pick it up.
- Removes obsolete 0.8 metre height filter and stops treating installed devices as being at ground level.
- The mobile controller now targets real world-space equipment bounds at the correct apartment, house and basement floor heights.
- Keeps other-floor objects from being selected through the ceiling; wall-placement rules and existing installed equipment remain unchanged.

SAFETY & TESTING
- All 55 production staff / equipment targeting checks and the full mobile runtime/gameplay suite passed.
- The public update builds pinned source, checks legacy saves, release identity, updater state and SHA-256 manifest before publishing.
- Preserves account login, cloud saves, existing crops, inventory, furniture, money and property ownership.
