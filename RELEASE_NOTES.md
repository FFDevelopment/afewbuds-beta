AFewBuds Mobile Beta 0.16.0-mobile-beta.15 — Basement Stairwell Visual Fix

VERIFIED MOBILE SOURCE
FFDevelopment/afewbuds-cloud-test main @ 27aa04f724cec2971fa092ce8bd89b8c77dae654
Mobile build and gameplay regression suite: https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38195626809

HOUSE BASEMENT — MOBILE VISUAL CORRECTION
- Cut the unwanted dark terrain/floor sheet covering the visible stairwell opening in the house.
- Handle ground-level decoration nested inside map containers, not just direct neighborhood mesh children.
- Remove visual-only zero-thickness ground planes from the opening as well as shallow box surfaces.
- Keep the walkable staircase, handrails, basement grow floor, existing player movement and collision layout intact.

PRESERVED FROM MOBILE BETA.14
- Full-sized Packing Bench III with functional house trimming/bagging and production worker animations.
- Larger physical house room boundaries and usable basement grow-room wing.
- Property-specific production staff, supplies, house deliveries, backpack upgrades, Grower level locks and Phone Shop equipment upgrades.
- Existing account identity, saves, property ownership, cash/bank, grow crops, tent upgrades, genetics and updater rollback.

VALIDATION
- Mobile pack generation, Godot import, mobile CharacterBody3D movement and progression passed.
- Map integration confirms the house stairwell is no longer covered by a visible terrain sheet; a nested visual-only plane regression is included.
- House room boundaries, packing parity, property isolation, equipment, staff, inventory and other mobile gameplay suites passed.
- Public release workflow independently rebuilds and tests pinned source, verifies updater/SHA-256 manifest, and deploys only after all gates pass.
