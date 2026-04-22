// ====== Shared Configuration and Helpers ======
const API_BASE = 'http://localhost:8001';

// Google Client ID will be fetched from backend
let GOOGLE_CLIENT_ID = null;

// MFA context/state
let mfaContext = null; // 'login' | 'register' | null
let lastLoginCreds = null; // { identifier, password }
let lastRegisterCreds = null; // { identifier, password }

// ====== Basic helpers ======
const out = document.getElementById('out');
function setOut(obj) {
  out.textContent = typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2);
}

// ====== Navigation helpers ======
function navigateTo(page) {
  window.location.href = page;
}

// ====== Google Identity Services ======
let latestIdToken = null;
let gisInitialized = false;

// Initialize GIS after fetching client ID from backend
async function initGoogle() {
  try {
    const res = await fetch(`${API_BASE}/auth/google/config`);
    const cfg = await res.json();
    if (!res.ok || !cfg.client_id) throw new Error('No client_id from backend');
    GOOGLE_CLIENT_ID = cfg.client_id;

    // Initialize the Google Identity Services client
    google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleGoogleCredentialResponse,
      auto_select: false
    });
    
    // Render the button inside #googleButton if it exists
    const googleButtonEl = document.getElementById('googleButton');
    if (googleButtonEl) {
      google.accounts.id.renderButton(googleButtonEl, {
        type: 'standard',
        size: 'large',
        theme: 'outline',
        text: 'sign_in_with',
        shape: 'rect',
        logo_alignment: 'left'
      });
    }
    gisInitialized = true;
  } catch (e) {
    setOut({ error: 'Failed to init Google button', details: e?.message || String(e) });
  }
}

// Handle GIS callback for sign-in
function handleGoogleCredentialResponse(resp) {
  latestIdToken = resp && resp.credential ? resp.credential : null;
  if (!latestIdToken) {
    setOut('No Google token received.');
    // Navigate to Google register page
    navigateTo('google_register.html');
    return;
  }
  setOut({ info: 'Google ID token received' });
  // Auto-attempt backend login
  googleLoginWithToken();
}

async function googleLoginWithToken() {
  if (!latestIdToken) {
    setOut('No token to login with.');
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/googleauthentication`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: latestIdToken })
    });
    const data = await res.json();
    setOut({ status: res.status, data });

    if (res.ok && data?.data?.access_token) {
      try { localStorage.setItem('access_token', data.data.access_token); } catch {}
      setOut('Google login successful! Redirecting to dashboard...');
      setTimeout(() => navigateTo('welcome.html'), 1500);
      return;
    }
    if (
      res.status === 404 ||
      (res.status === 400 && (
        (data?.detail || '').includes('First-time Google sign-in requires phone and role_id') ||
        (data?.message || '').includes('First-time Google sign-in requires phone and role_id') ||
        (data?.data?.message || '').includes('First-time Google sign-in requires phone and role_id')
      ))
    ) {
      // Not registered yet — navigate to Google register page
      navigateTo('google_register.html');
    }
  } catch (e) {
    setOut({ error: e?.message || String(e) });
  }
}

// ====== MFA helpers ======
function openMfaPanel(identifier, { showStart = true, autoStart = true } = {}) {
  // Store data in sessionStorage to pass to MFA page
  sessionStorage.setItem('mfa_identifier', identifier);
  sessionStorage.setItem('mfa_context', mfaContext || '');
  sessionStorage.setItem('mfa_show_start', showStart.toString());
  sessionStorage.setItem('mfa_auto_start', autoStart.toString());
  
  // Store credentials for post-MFA login if needed
  if (lastLoginCreds) {
    sessionStorage.setItem('last_login_creds', JSON.stringify(lastLoginCreds));
  }
  if (lastRegisterCreds) {
    sessionStorage.setItem('last_register_creds', JSON.stringify(lastRegisterCreds));
  }
  
  navigateTo('mfa.html');
}

async function mfaStart() {
  const identifier = document.getElementById('mfa-identifier').value.trim();
  if (!identifier) { setOut('Enter an identifier first.'); return; }
  try {
    const res = await fetch(`${API_BASE}/auth/mfa/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier })
    });
    const data = await res.json();
    setOut({ status: res.status, data });
    if (!res.ok) return;

    const { otpauth_url, secret } = data;
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(otpauth_url)}`;
    document.getElementById('mfa-qr').src = qrUrl;
    document.getElementById('mfa-secret').textContent = secret;
    document.getElementById('mfa-otpauth').href = otpauth_url;
    document.getElementById('mfa-setup-panel').classList.remove('hidden');
  } catch (e) {
    setOut({ error: e?.message || String(e) });
  }
}

async function mfaVerify() {
  const identifier = document.getElementById('mfa-identifier').value.trim();
  const code = document.getElementById('mfa-code').value.trim();
  if (!identifier || !code) { setOut('Provide identifier and 6-digit code.'); return; }
  if (!/^\d{6}$/.test(code)) { setOut('Code must be 6 digits.'); return; }
  
  try {
    const purpose = (mfaContext === 'register') ? 'register' : 'login';
    const res = await fetch(`${API_BASE}/auth/mfa/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identifier, code, purpose })
    });
    const data = await res.json();
    setOut({ status: res.status, data });

    // If backend returns token (old behavior), store it
    const token = data?.data?.access_token;
    if (res.ok && token) {
      try { localStorage.setItem('access_token', token); } catch {}
      setOut('MFA verification successful! Redirecting to dashboard...');
      setTimeout(() => navigateTo('welcome.html'), 1500);
      return;
    }

    // If backend returns only success (new behavior), complete the flow
    if (res.ok && !token) {
      // If user opted-in at register, enable authenticator after successful verify
      if (mfaContext === 'register') {
        try {
          await fetch(`${API_BASE}/auth/mfa/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier, enabled: true })
          });
        } catch {}
      }

      // Finish login automatically if we came from login
      if (mfaContext === 'login' && lastLoginCreds) {
        try {
          const r2 = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...lastLoginCreds, code })
          });
          const d2 = await r2.json();
          setOut({ after_verify_login_status: r2.status, data: d2 });
          if (r2.ok && d2?.data?.access_token) {
            try { localStorage.setItem('access_token', d2.data.access_token); } catch {}
            setOut('Login after MFA successful! Redirecting to dashboard...');
            setTimeout(() => navigateTo('welcome.html'), 1500);
            return;
          }
        } catch (e) {
          setOut({ error: 'Post-verify login failed', details: e?.message || String(e) });
        }
      }

      // Try to login automatically after registration verification
      if (mfaContext === 'register' && lastRegisterCreds) {
        try {
          const r3 = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...lastRegisterCreds, code })
          });
          const d3 = await r3.json();
          setOut({ after_verify_reg_login_status: r3.status, data: d3 });
          if (r3.ok && d3?.data?.access_token) {
            try { localStorage.setItem('access_token', d3.data.access_token); } catch {}
            setOut('Registration and login successful! Redirecting to dashboard...');
            setTimeout(() => navigateTo('welcome.html'), 1500);
            return;
          }
        } catch (e) {
          setOut({ error: 'Post-verify registration login failed', details: e?.message || String(e) });
        }
      }

      setOut('TOTP verified successfully! Redirecting to dashboard...');
      setTimeout(() => navigateTo('welcome.html'), 1500);
    }
  } catch (e) {
    setOut({ error: e?.message || String(e) });
  }
}

// ====== Auto-initialize Google when available ======
function initGoogleWhenReady() {
  if (window.google && window.google.accounts && window.google.accounts.id) {
    initGoogle();
  } else {
    // If GIS script loads async, wait a bit and retry
    const i = setInterval(() => {
      if (window.google && window.google.accounts && window.google.accounts.id) {
        clearInterval(i);
        initGoogle();
      }
    }, 200);
    setTimeout(() => clearInterval(i), 5000);
  }
}

// Start Google init once the page has loaded
window.addEventListener('DOMContentLoaded', initGoogleWhenReady);