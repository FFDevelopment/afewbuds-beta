AFewBuds Mobile Beta 0.16.0-mobile-beta.14 — Full House Packing & Basement Production Fix

VERIFIED MOBILE SOURCE
FFDevelopment/afewbuds-cloud-test main @ 2203f328229921ddbf4838b6ebbd464119f79bbc
Mobile build and Godot game tests: https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38184046312

HOUSE PACKING WORKFLOW
- Purchased Packing Bench III now matches the full-size finished apartment model, complete with scale, tabletop, jar layout and trim tray.
- Fix actual hand trimming and bagging at the house bench. Stock is taken from and returned to the house's own packing station, with real scoop, fill and seal steps.
- Production workers animate trim/bag operations at the real packing bench rather than an unrelated apartment work station.
- Full-size benches can be placed close to the usable packing-room wall, with structural walls, stairs, doorways and other furniture still preventing clipping.

HOUSE BOUNDARIES & BASEMENT
- All upstairs house rooms use their physical interior wall faces for safe placement rather than narrower legacy rectangles.
- Basement grow-room floor now includes the usable eastern wing, so growers can place tents where there is actual floor without entering the stair or railing areas.
- Basement furniture, packing stations and inventory interaction areas remain on the lower floor. House and apartment stock cannot mix.

WORKERS, PROGRESSION AND EXISTING CAREER
- Retains one independently hired, managed and paid production worker at each owned property, with specific roles, per-property schedules, finite supplies and transfer rules.
- Retains Level I shop purchases followed by item-specific upgrades, Grower-level unlock requirements, per-tent LED upgrades, property deliveries, backpack space upgrades and Phone Shop browsing.
- Preserves existing characters, property and equipment ownership, purchases, bank/cash balances, genetics, growing crops, account cloud saves, mobile PWA identity and update rollback.

RELEASE VALIDATION
- Candidate source passed 36 production staff, 37 shop, 44 structural bounds/basement, 33 packing parity, 88 property-isolation and 85 equipment Godot checks.
- Public beta publication additionally builds the pinned source, reruns mandatory tests, checks saved career/session/update behavior, validates hashes and deploys Pages only after all gates pass.
