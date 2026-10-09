# AFewBuds Mobile Beta

[Play or install AFewBuds](https://ffdevelopment.github.io/afewbuds-beta/)

This is the main public mobile repository. Use the browser's Add to Home Screen / Install App option to install it. Existing installations keep the same address, icon, sign-in, and save data.

Opening the app or web page checks for an update. Downloads are verified before activation; the previous installed release is retained for rollback. Returning to an already-open app also checks for updates and saves the active career before switching versions. If saving fails, the update waits for a retry.

Sign in to load the latest confirmed account career shared with the [desktop beta](https://github.com/FFDevelopment/AFewBuds-Desktop-Beta/releases). One active play session is allowed per account. The old device pauses during handoff. Signed-in play requires a connection to verify the career and session. Guests keep a local career.

The original public-beta device save is preserved. If it contains newer unsynced progress associated with your account, the launcher offers a choice before replacing the cloud career. It never imports another account's local save. Keep the app's storage when updating; reinstalling or clearing site data is unnecessary.

## Release workflow

Current release: **0.16.0-mobile-beta.6**. The game pack is rebuilt from its pinned source and passes the mobile gameplay and property-isolation checks before publication. `RELEASE_INTEGRITY.json` records its source and checksum.

Run `python tools/manifest.py --check` and `node tools/shared_save_test.cjs` before publication. The Pages workflow verifies the release manifest and launcher tests before deploying.

The cloud-test and 3D-prototype repositories remain development/test repositories. Promote verified candidates here; do not run retired promotion scripts against main. Historical scripts and receipts are in `archive/`, outside the deployed site. The `archive/accountsync14-before-mobile3d` tag preserves the complete previous public baseline. The previous public game pack remains available as a compatibility fallback.
