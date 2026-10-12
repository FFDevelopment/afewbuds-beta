AFewBuds Mobile Beta 0.16.0-mobile-beta.16 — House Basement Stairwell Render Hotfix

VERIFIED MOBILE SOURCE
FFDevelopment/afewbuds-cloud-test main @ 0a5e8f6d558e36e2ab488e3377a1bed025166b04
Mobile build and gameplay regression checks: https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38198981255
Actual OpenGL render captures of the mobile stairwell: https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38198981253

CORRECTED HOUSE BASEMENT
- Fix black speckled terrain covering the stairs in the house on iPhone/mobile.
- Root cause: one oversized exterior terrain slab had been batched into a MultiMeshInstance3D, so prior ordinary MeshInstance3D floor cutting did not affect it.
- Split that specific terrain slab into four surrounding pieces with a 3.5 m by 5.3 m stairwell opening before rendering/batching, preserving the exterior ground outside the opening.
- Confirmed by real mobile runtime OpenGL captures: both stair flights, handrails and landing are visible from above and from the upstairs landing.
- Preserve original stair collisions, walking, basement floor, furniture placement, NPC routing and exterior neighborhood geometry.

PRESERVED FROM MOBILE BETA.15
- Full-sized Packing Bench III with manual trimming/bagging and production NPC animations, basement placement boundaries, property staff, market deliveries, backpack equipment, station upgrades and Phone Shop.
- Save data, bank/cash balances, crops, genetics, property ownership, staff contracts, mobile session identity and updater rollback.

PUBLIC RELEASE VALIDATION
- Pinned verified mobile source is rebuilt and tested independently by the public beta workflow.
- Mandatory in-engine gameplay, property-isolation, inventory and movement tests plus updater/manifest checksum validations gate publication.
