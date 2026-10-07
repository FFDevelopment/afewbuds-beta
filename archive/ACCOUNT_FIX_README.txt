AFewBuds beta.16 account fix

This package deliberately keeps the known-good beta.16 Godot runtime and moves sign-in/sign-up to a native HTML overlay outside the canvas. This fixes desktop click/typing and mobile keyboard reliability.

IMPORTANT BACKEND PATCH
Run supabase/PATCH_EXISTING.sql once in your existing Supabase project's SQL Editor. It updates afb_make_session so login/register responses also include account_id. No player accounts are deleted.

UPLOAD
Copy every file/folder in this package into the root of your existing afewbuds-beta GitHub repository and replace matching files. Commit and push.

Accounts
- username uniqueness remains case-insensitive
- optional email/update opt-in
- remember-me supported
- Continue without an account remains available
- analytics tracker starts after the user chooses a path into the game
