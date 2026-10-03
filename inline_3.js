
const GODOT_CONFIG = {"args":[],"canvasResizePolicy":2,"emscriptenPoolSize":8,"ensureCrossOriginIsolationHeaders":false,"executable":"index","experimentalVK":true,"fileSizes":{"index.pck":25354652,"index.wasm":37902138},"focusCanvas":true,"gdextensionLibs":[],"godotPoolSize":4,"serviceWorker":"index.service.worker.js"};
const GODOT_THREADS_ENABLED = false;
let AFB_GAME_STARTED = false;

function afbSetPane(which) {
	const login = which === 'login';
	document.getElementById('afb-login-tab').classList.toggle('active', login);
	document.getElementById('afb-register-tab').classList.toggle('active', !login);
	document.getElementById('afb-login-pane').hidden = !login;
	document.getElementById('afb-register-pane').hidden = login;
	setTimeout(() => (login ? document.getElementById('afb-login-user') : document.getElementById('afb-register-user')).focus(), 0);
}
function afbMessage(id, text, bad=false) {
	const el = document.getElementById(id);
	el.textContent = text || '';
	el.classList.toggle('bad', !!bad);
}
function afbFriendlyError(error) {
	const raw = String(error && error.message || error || 'Account request failed.');
	if (/username_taken|duplicate|unique/i.test(raw)) return 'That username is already taken.';
	if (/username_invalid/i.test(raw)) return 'Use 3–20 letters, numbers, or underscores for the username.';
	if (/password_too_short/i.test(raw)) return 'Use a password with at least 8 characters.';
	if (/email_required_for_updates/i.test(raw)) return 'Enter an email address or turn off update emails.';
	if (/invalid_username_or_password/i.test(raw)) return 'That username or password is not correct.';
	if (/session_invalid/i.test(raw)) return 'Your saved sign-in expired. Please sign in again.';
	return raw;
}
function afbNormalizeSession(data) {
	if (Array.isArray(data)) data = data[0] || null;
	if (data && data.value && typeof data.value === 'object') data = data.value;
	return data && typeof data === 'object' ? data : null;
}
async function afbValidateStoredSession() {
	if (!window.AFB_API || !AFB_API.enabled) return null;
	const saved = AFB_API.getPlayerSession();
	if (!saved || !saved.session_token) return null;
	try {
		const verified = afbNormalizeSession(await AFB_API.rpc('afb_validate_session', {p_session_token:saved.session_token}));
		if (!verified || !verified.username) throw new Error('session_invalid');
		const merged = Object.assign({}, saved, verified, {session_token:saved.session_token});
		AFB_API.savePlayerSession(merged, !!localStorage.getItem('afb_player_session'));
		return merged;
	} catch (_) {
		AFB_API.clearPlayerSession();
		return null;
	}
}
function afbLoadTracker() {
	if (document.getElementById('afb-tracker-script')) return;
	const s = document.createElement('script');
	s.id = 'afb-tracker-script';
	s.src = 'shared/afb-tracker.js?v=0.7.9-beta.16-accountfix1';
	document.body.appendChild(s);
}
function afbLaunchGame() {
	if (AFB_GAME_STARTED) return;
	AFB_GAME_STARTED = true;
	document.getElementById('afb-account-gate').hidden = true;
	afbLoadTracker();
	launchGodotEngine();
}
function launchGodotEngine() {
	const engine = new Engine(GODOT_CONFIG);
	const statusOverlay = document.getElementById('status');
	const statusProgress = document.getElementById('status-progress');
	const statusNotice = document.getElementById('status-notice');
	let initializing = true;
	let statusMode = '';
	function setStatusMode(mode) {
		if (statusMode === mode || !initializing) return;
		if (mode === 'hidden') { statusOverlay.remove(); initializing = false; return; }
		statusOverlay.style.visibility = 'visible';
		statusProgress.style.display = mode === 'progress' ? 'block' : 'none';
		statusNotice.style.display = mode === 'notice' ? 'block' : 'none';
		statusMode = mode;
	}
	function setStatusNotice(text) {
		while (statusNotice.lastChild) statusNotice.removeChild(statusNotice.lastChild);
		String(text).split('\n').forEach((line) => { statusNotice.appendChild(document.createTextNode(line)); statusNotice.appendChild(document.createElement('br')); });
	}
	function displayFailureNotice(err) {
		console.error(err);
		setStatusNotice(err instanceof Error ? err.message : (typeof err === 'string' ? err : 'An unknown error occurred.'));
		setStatusMode('notice'); initializing = false;
	}
	const missing = Engine.getMissingFeatures({threads:GODOT_THREADS_ENABLED});
	if (missing.length !== 0) {
		displayFailureNotice('Error\nThe following features required to run Godot projects on the Web are missing:\n' + missing.join('\n'));
		return;
	}
	setStatusMode('progress');
	engine.startGame({onProgress:function(current,total){
		if (current > 0 && total > 0) { statusProgress.value=current; statusProgress.max=total; }
		else { statusProgress.removeAttribute('value'); statusProgress.removeAttribute('max'); }
	}}).then(() => setStatusMode('hidden'), displayFailureNotice);
}

document.getElementById('afb-login-tab').addEventListener('click', () => afbSetPane('login'));
document.getElementById('afb-register-tab').addEventListener('click', () => afbSetPane('register'));
document.getElementById('afb-guest-btn').addEventListener('click', afbLaunchGame);
document.getElementById('afb-login-form').addEventListener('submit', async (event) => {
	event.preventDefault();
	const button = document.getElementById('afb-login-btn'); button.disabled = true;
	afbMessage('afb-login-msg', 'Signing in…');
	try {
		if (!window.AFB_API || !AFB_API.enabled) throw new Error('Account service is not configured. You can continue without an account.');
		let data = afbNormalizeSession(await AFB_API.rpc('afb_login', {
			p_username:document.getElementById('afb-login-user').value.trim(),
			p_password:document.getElementById('afb-login-pass').value,
			p_remember:document.getElementById('afb-login-remember').checked
		}));
		if (!data || !data.session_token || !data.username) throw new Error('Account service returned an incomplete sign-in.');
		AFB_API.savePlayerSession(data, document.getElementById('afb-login-remember').checked);
		afbMessage('afb-login-msg', 'Signed in as ' + data.username + '.');
		afbLaunchGame();
	} catch (e) { afbMessage('afb-login-msg', afbFriendlyError(e), true); }
	finally { button.disabled = false; }
});
document.getElementById('afb-register-form').addEventListener('submit', async (event) => {
	event.preventDefault();
	const button = document.getElementById('afb-register-btn'); button.disabled = true;
	afbMessage('afb-register-msg', 'Creating account…');
	try {
		if (!window.AFB_API || !AFB_API.enabled) throw new Error('Account service is not configured. You can continue without an account.');
		let data = afbNormalizeSession(await AFB_API.rpc('afb_register', {
			p_username:document.getElementById('afb-register-user').value.trim(),
			p_password:document.getElementById('afb-register-pass').value,
			p_email:document.getElementById('afb-register-email').value.trim() || null,
			p_updates_opt_in:document.getElementById('afb-register-updates').checked,
			p_remember:document.getElementById('afb-register-remember').checked
		}));
		if (!data || !data.session_token || !data.username) throw new Error('Account service returned an incomplete registration.');
		AFB_API.savePlayerSession(data, document.getElementById('afb-register-remember').checked);
		afbMessage('afb-register-msg', 'Account created. Welcome, ' + data.username + '.');
		afbLaunchGame();
	} catch (e) { afbMessage('afb-register-msg', afbFriendlyError(e), true); }
	finally { button.disabled = false; }
});

(async function bootAccountGate(){
	const saved = await afbValidateStoredSession();
	if (saved) { afbLaunchGame(); return; }
	const gate = document.getElementById('afb-account-gate');
	gate.hidden = false;
	if (!window.AFB_API || !AFB_API.enabled) {
		afbMessage('afb-login-msg', 'Account service is not configured yet. You can continue without an account.', true);
	}
})();
		