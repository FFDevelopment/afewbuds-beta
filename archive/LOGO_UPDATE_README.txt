HISTORICAL beta.5 branding notes. Current build: 0.7.9-beta.1.
Use UPLOAD_INSTRUCTIONS.txt for this release.

AFewBuds 0.7.8-beta.5 — AFB logo integration

WHAT CHANGED
The supplied neon AFB artwork is now the shared AFewBuds branding:
- Godot project/default application icon and boot splash.
- Browser tab icon, Apple touch icon and PWA installation icons (144/180/192/512).
- Web loading page, offline page and optional browser-update repair page.
- In-game phone header (all its sections), first-day intro and pause/return panel.
UI logos preserve their aspect ratio and do not intercept input.

NO BLACK CORNERS
The game/UI and splash use transparent PNGs. Launcher/Home Screen icons use a
solid emerald background instead of transparent/black corners, so the operating
system can apply its own rounded mask. The original artwork is not redrawn or cropped.
The separate Logo Assets ZIP also includes transparent and opaque 1024px masters.

GODOT / XOGOT
Use the editable project ZIP, not the GitHub Pages ZIP. Extract and open project.godot.
To retain an existing Xogot career, back up the existing project and update its source
in place rather than deleting it. No .godot cache or exported Web engine is bundled.
Project Settings > Application > Config > Icon:
  res://assets/branding/afb_app_icon.png
Project Settings > Application > Boot Splash > Image:
  res://assets/branding/afb_splash.png
Shared in-game logo:
  res://assets/branding/afb_logo.png (APP_LOGO in scripts/main.gd)
Keep application/config/name exactly as supplied. Its older-looking version text is
intentional: the established save directory identity is not renamed for branding.
The actual running build is 0.7.8-beta.5, shown in Phone > Help.

GITHUB PAGES
Extract the GitHub Pages ZIP. Copy its CONTENTS beside the existing index.html in
local afewbuds-beta, replacing the exported files. Do not add an extra parent folder.
Keep your .git folder. If you already have custom .gitattributes, retain its rules
and merge the included binary rules rather than discarding your configuration.
Commit to main, Push origin, and wait for a successful Pages deployment in Actions.
The existing game link stays the same. This package does not publish anything itself.

CACHING / OLD HOME SCREEN ICONS
Close old game windows before reopening after the successful deployment. Check
Phone > Help for beta.5. To inspect a newly installed iPhone icon, open the site in
Safari and use Share > Add to Home Screen (Open as Web App where offered).
This does not guarantee an already-installed shortcut refreshes its image immediately.
Do not delete an existing game install or clear website data just to change the picture.
The optional afewbuds-update.html repair page is included and now verifies THIS build,
not beta.4. It handles browser game caches only and never reads or deletes saves.

FUTURE WEB EXPORTS
Export the Web PWA preset using Export Project to build/web/index.html.
Then run from this project folder:
  python web/finalize_export.py build/web
This standard-library Python 3 step applies public names/icon URLs, increments the
cache tag and rebuilds repair checksums for the exact files you just exported.
EXPORT_WEB.bat attempts this step automatically when Python 3 is available.
Web exports made directly on another platform can be finalized later on your computer.

SAVE / GAMEPLAY COMPATIBILITY
This is a logo-only update. Save filename, schema, project identity and PWA start_url
are unchanged. Plant growth, offline rules, workers, tutorials, phone scrolling and
physical switches retain beta.4 logic. No career reset is required by these changes.

VALIDATION
See tests/TESTING.md in the source project. Headless engine/resource/layout checks
passed; no physical iPhone/Xogot/Safari icon installation has been tested here.
