AFewBuds Mobile Beta 0.16.0-mobile-beta.11 — Packing Bench, Delivery & Backpack Hotfix

Exact isolated source: FFDevelopment/afewbuds-cloud-test @ 3b060670f270dddc3d5a4b25ba4da0ce856a9cb8
Source branch: hotfix/testers-shop-bench-delivery-backpack-20261011. Experimental character creator/art and Mission & Story changes excluded.

FIXED
- Purchased packing benches now reuse the approved detailed apartment bench art (work surface, electronic scale, trim tray, bag box, jars and supplies) instead of the market's simplified placeholder. Placement preview uses the same detailed assembly.
- Packing stations continue to use the original hands-on scissors trimming and drag-to-bag/scale/sealing minigames, with the purchased bench and active property's stock.
- Market Cart checkout now offers Market Pickup or owned Apartment/House curbside delivery for furniture and equipment. Paid crates remain at the destination until collected; seeds and fertilizer still follow Central Market pickup. Property ownership is checked BEFORE payment.
- Central Market > Upgrades again shows the saved backpack level and lets players purchase the next permanent capacity tier (35 / 55 / 80 / 110 lb; upgrade prices $250 / $750 / $1,750).
- Phone > Shop > Shop Upgrades now shows backpack capacities/prices and equipment families without remote purchasing. Backpack purchases remain at Central Market checkout.

UNCHANGED
- House furniture arrangement was already fixed in beta.10 and is not replaced.
- Production worker planting cadence and stock consumption have not been modified.
- Existing purchases, furniture placements, store inventories, worker assignments, genetics, story, account/login, save schema and cloud sync are preserved.
- Existing home-screen PWA URL, SHA-256-verified updater, installation identity and safe rollback are unchanged.

Release gates: full mobile Godot movement, ownership, packaging, delivery, backpack and save regression suite; mobile package import, cloud migration and updater checks; verified artifact SHA-256 and successful Pages deployment. No beta is live until these gates pass.
