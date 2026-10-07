# Public mobile release repository

- `FFDevelopment/afewbuds-beta` is the main public mobile repository and updater endpoint. Preserve its URL, manifest start URL, service-worker scope, `afb_player_session` login key, and user save data.
- `FFDevelopment/AFewBuds-Desktop-Beta` distributes the public desktop beta. `afewbuds-cloud-test` and `afewbuds-3d-prototype` are development/test repositories.
- Promote only tested candidates. Keep shared gameplay/save behavior paired while preserving platform-specific controls.
- Validate manifest sizes/SHA-256 hashes, update rollback, existing-save migration, and session fencing before publishing. Never clear IndexedDB/localStorage or unrelated application caches during an update.
- Historical promotion scripts/workflows under archive are references only. The supported deployment is `.github/workflows/pages.yml`.
- Chapter 4 ends after property relocation and first house entry. Chapter 5 has its opening, not a complete mission chain.
