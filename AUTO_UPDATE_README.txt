AFewBuds Automatic Updater v1

Release: 0.7.9-beta.16-autoupdater1
Game runtime: known-good 0.7.9-beta.16

How it works:
- index.html runs the pre-launch updater before account login or Godot.
- version.json is always requested from the network.
- new releases download into a temporary versioned CacheStorage cache.
- every staged file is checked for byte size and SHA-256 before activation.
- the previous release cache is retained for rollback.
- a newly activated release remains pending until the Godot engine starts successfully.
- failed or timed-out game startup restores the previous release.
- if the update check is offline/unavailable, the installed release starts normally.
- updater caches never clear localStorage or IndexedDB.

FIRST MIGRATION FROM THE OLD CACHE SYSTEM:
After uploading this package and waiting for GitHub Pages to deploy, open /afewbuds-update.html once and press Repair. This removes only the legacy AFewBuds application cache/service worker, then the automatic updater takes over.

FOR FUTURE RELEASES:
Keep index.service.worker.js and shared/afb-updater.js in the package. Generate a new version.json with a new release_id and SHA-256/size values for the shipped app files. The launcher will update before starting the game only when release_id changes.
