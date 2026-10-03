(function () {
  const cfg = window.AFB_CONFIG || {};
  const base = (cfg.supabaseUrl || '').replace(/\/$/, '');
  const apiKey = cfg.supabasePublishableKey || cfg.supabaseAnonKey || '';
  const enabled = /^https:\/\//.test(base) && apiKey && !apiKey.includes('YOUR_SUPABASE');

  function headers(extra) {
    return Object.assign({
      'Content-Type': 'application/json',
      'apikey': apiKey
    }, extra || {});
  }

  async function rpc(name, payload, bearer) {
    if (!enabled) throw new Error('Backend is not configured yet.');
    const res = await fetch(base + '/rest/v1/rpc/' + name, {
      method: 'POST',
      headers: headers(bearer ? {'Authorization': 'Bearer ' + bearer} : null),
      body: JSON.stringify(payload || {})
    });
    let data = null;
    const text = await res.text();
    if (text) {
      try { data = JSON.parse(text); } catch (_) { data = text; }
    }
    if (!res.ok) {
      const message = data && (data.message || data.error_description || data.error) || ('Request failed (' + res.status + ')');
      throw new Error(message);
    }
    return data;
  }

  async function adminLogin(email, password) {
    if (!enabled) throw new Error('Backend is not configured yet.');
    const res = await fetch(base + '/auth/v1/token?grant_type=password', {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({email, password})
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error_description || data.msg || 'Admin login failed.');
    return data;
  }

  function savePlayerSession(value, remember) {
    const key = 'afb_player_session';
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
    (remember ? localStorage : sessionStorage).setItem(key, JSON.stringify(value));
  }
  function getPlayerSession() {
    const raw = localStorage.getItem('afb_player_session') || sessionStorage.getItem('afb_player_session');
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (_) { return null; }
  }
  function clearPlayerSession() {
    localStorage.removeItem('afb_player_session');
    sessionStorage.removeItem('afb_player_session');
  }

  function deviceId() {
    const key = 'afb_device_id';
    let value = localStorage.getItem(key);
    if (!value) {
      value = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + '-' + Math.random().toString(16).slice(2));
      localStorage.setItem(key, value);
    }
    return value;
  }

  window.AFB_API = {
    enabled,
    cfg,
    rpc,
    adminLogin,
    savePlayerSession,
    getPlayerSession,
    clearPlayerSession,
    deviceId
  };
}());
