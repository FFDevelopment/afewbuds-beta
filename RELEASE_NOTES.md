AFewBuds Mobile Beta 0.16.0-mobile-beta.10 — House Furniture Arrange Hotfix

Source: FFDevelopment/afewbuds-cloud-test @ 9f30f9159afd7db9ab9921681884217927f58b67 (isolated hotfix forked directly from the validated 0.16.0-mobile-beta.9 game source, without unfinished development features).

- FIX: Property Manager > Maple Flats House > ARRANGE FURNITURE is now available whenever the owner is physically inside their house, even if Starter Apartment remains their primary operation.
- Repair the property-presence check; the house and apartment are checked against the character's current physical room, never the saved primary operation.
- Players outside the property or inside their other property still cannot rearrange house furniture.
- The existing furniture editor, Move / Unlock / Pick up / Walk-around controls and collision/placement rules are unchanged.
- No furniture, saved positions, tents, workers, property assignments, money, progression, avatar data or inventory are changed or migrated.
- Regression specifically checks that phone button is enabled inside owned house while apartment is primary; opens the correct house editor; requires on-site ownership and leaves saved furniture exactly unchanged.
- Preserve existing URL, home-screen PWA updater, cloud-login/session protocol, career save schema and safe rollback. Does NOT include experimental character meshes or the unfinished mission system.

The official release pipeline rebuilds this pinned hotfix and reruns the full Godot movement/property/inventory/save suite and the mobile updater/legacy-career migration tests before deployment.
