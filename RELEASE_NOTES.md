AFewBuds Mobile Beta 0.16.0-mobile-beta.18 — Multi-Storage Listing & Sale Accounting

VERIFIED MOBILE SOURCE
- FFDevelopment/afewbuds-cloud-test main @ bb6277a3bd4e5411a1ce0f26a95e86849582005c
- Full mobile tests: https://github.com/FFDevelopment/afewbuds-cloud-test/actions/runs/38294851284
- Multi-storage regression: 28/28 passed, plus inventory, property isolation, equipment and gameplay checks.

MULTIPLE STORAGE UNITS PER PROPERTY
- Phone stock/listing quantities now combine the packaged weed from every installed storage shelf, vault or stash at the selected property.
- Reserving product subtracts reserved grams from that property's aggregated stock exactly once.
- New strain labels from secondary storage are selectable even if the legacy primary stock is empty.
- Selling product draws the requested grams across physical storage units in order, without duplicates, negative balances or consuming reserved stock.
- Door dealer sales, friend purchases, and transfers to/from Dealer Locker use the same safe stock debit.
- Production worker and manual packing deposits fill available shelves individually without overfilling one unit.
- Apartment and house quantities, listings, and reserves remain separate.
- Property overview and Storage menu now reflect all actual installed units. Packed/uninstalled furniture does not contribute ghost stock.

SAVES AND UPDATER
- No player migration or wipe: existing container IDs, inventory data, property ownership, customer relationships, cloud identity and updater settings are preserved.
- Public release pipeline independently builds pinned source and verifies previous saved-account compatibility, deployment files, and SHA-256 manifests.
