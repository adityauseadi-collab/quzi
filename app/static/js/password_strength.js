/**
 * QuizMaster Pro — Password Strength Meter
 * =========================================
 * Attaches a real-time strength indicator to any <input type="password">
 * that carries the attribute  data-strength-meter="true".
 *
 * Usage (HTML):
 *   <input type="password" id="password" data-strength-meter="true">
 *
 * The script:
 *  1. Debounces keystrokes and calls /auth/api/password-strength (POST).
 *  2. Renders a segmented progress bar, strength label, and per-rule checklist.
 *  3. Exposes window.PasswordStrength for manual invocation.
 */

(function () {
  'use strict';

  /* ── Configuration ────────────────────────────────────────────────────────── */
  const API_ENDPOINT = '/auth/api/password-strength';
  const DEBOUNCE_MS  = 250;

  /* ── Labels & colours ─────────────────────────────────────────────────────── */
  const LEVELS = {
    Weak:   { cls: 'weak',   icon: '🔴', label: '❌ Weak'   },
    Medium: { cls: 'medium', icon: '🟡', label: '⚠️ Medium' },
    Strong: { cls: 'strong', icon: '🟢', label: '✅ Strong' },
  };

  /* ── Static rules shown in the checklist ─────────────────────────────────── */
  const RULES = [
    { id: 'len',     label: 'At least 8 characters',        test: p => p.length >= 8 },
    { id: 'upper',   label: 'At least one uppercase letter', test: p => /[A-Z]/.test(p) },
    { id: 'lower',   label: 'At least one lowercase letter', test: p => /[a-z]/.test(p) },
    { id: 'digit',   label: 'At least one number',           test: p => /\d/.test(p)    },
    { id: 'special', label: 'Special character (recommended)',test: p => /[^A-Za-z0-9]/.test(p) },
  ];

  /* ── Build the meter DOM once per field ──────────────────────────────────── */
  function buildMeter(inputEl) {
    const wrap = document.createElement('div');
    wrap.className = 'pwd-strength-wrap';
    wrap.innerHTML = `
      <div class="pwd-bar-track">
        <div class="pwd-bar-fill" id="bar-${inputEl.id}"></div>
      </div>
      <div class="pwd-label-row">
        <span class="pwd-strength-text" id="lbl-${inputEl.id}"></span>
        <div class="pwd-dots">
          <div class="pwd-dot" id="dot0-${inputEl.id}"></div>
          <div class="pwd-dot" id="dot1-${inputEl.id}"></div>
          <div class="pwd-dot" id="dot2-${inputEl.id}"></div>
        </div>
      </div>
      <ul class="pwd-requirements" id="reqs-${inputEl.id}">
        ${RULES.map(r => `
          <li class="pwd-req-item" id="req-${r.id}-${inputEl.id}">
            <span class="pwd-req-icon">○</span>
            <span>${r.label}</span>
          </li>`).join('')}
      </ul>
      <div class="pwd-suggestion" id="sug-${inputEl.id}"></div>
    `;

    // Insert immediately after the input (or its input-group wrapper)
    const target = inputEl.closest('.input-group') || inputEl;
    target.insertAdjacentElement('afterend', wrap);

    // Also inject a live strength badge next to the <label>
    const labelEl = document.querySelector(`label[for="${inputEl.id}"]`);
    if (labelEl && !labelEl.querySelector('.pwd-badge')) {
      const badge = document.createElement('span');
      badge.className = 'pwd-badge hidden';
      badge.id = `badge-${inputEl.id}`;
      labelEl.appendChild(badge);
    }
  }

  /* ── Update the UI from an API result object ─────────────────────────────── */
  function updateUI(inputEl, result, password) {
    const id  = inputEl.id;
    const lvl = LEVELS[result.strength] || LEVELS.Weak;

    /* bar fill */
    const bar = document.getElementById(`bar-${id}`);
    if (bar) { bar.className = `pwd-bar-fill ${lvl.cls}`; }

    /* label */
    const lbl = document.getElementById(`lbl-${id}`);
    if (lbl) {
      lbl.textContent = password ? lvl.label : '';
      lbl.className   = `pwd-strength-text ${password ? lvl.cls : ''}`;
    }

    /* dots */
    const dotCls = { Weak: ['weak','',''], Medium: ['medium','medium',''], Strong: ['strong','strong','strong'] };
    const dots = dotCls[result.strength] || ['','',''];
    [0, 1, 2].forEach(i => {
      const d = document.getElementById(`dot${i}-${id}`);
      if (d) d.className = `pwd-dot ${dots[i]}`;
    });

    /* badge next to label */
    const badge = document.getElementById(`badge-${id}`);
    if (badge) {
      if (password) {
        badge.textContent = result.strength;
        badge.className   = `pwd-badge ${lvl.cls}`;
      } else {
        badge.className = 'pwd-badge hidden';
      }
    }

    /* rule checklist */
    const reqs = document.getElementById(`reqs-${id}`);
    if (reqs) {
      reqs.classList.toggle('visible', password.length > 0);
      RULES.forEach(r => {
        const li   = document.getElementById(`req-${r.id}-${id}`);
        if (!li) return;
        const pass = r.test(password);
        li.className = `pwd-req-item ${pass ? 'ok' : (password ? 'fail' : '')}`;
        li.querySelector('.pwd-req-icon').textContent = pass ? '✓' : (password ? '✗' : '○');
      });
    }

    /* suggestion */
    const sug = document.getElementById(`sug-${id}`);
    if (sug) {
      sug.textContent = (result.suggestions && result.suggestions[0]) || '';
    }
  }

  /* ── Fetch strength from backend ─────────────────────────────────────────── */
  async function fetchStrength(password) {
    try {
      const res = await fetch(API_ENDPOINT, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ password }),
      });
      return await res.json();
    } catch {
      /* Fallback: client-side only */
      return clientSideFallback(password);
    }
  }

  /* ── Pure-JS fallback (no network) ──────────────────────────────────────── */
  function clientSideFallback(p) {
    const errors = [];
    let score = 0;
    if (p.length >= 8) score++; else errors.push('Password must be at least 8 characters long.');
    if (p.length >= 12) score++;
    if (/[A-Z]/.test(p)) score++; else errors.push('Add an uppercase letter.');
    if (/[a-z]/.test(p)) score++; else errors.push('Add a lowercase letter.');
    if (/\d/.test(p))    score++; else errors.push('Add a number.');
    if (/[^A-Za-z0-9]/.test(p)) score++;
    const strength = score <= 2 ? 'Weak' : score <= 4 ? 'Medium' : 'Strong';
    return { valid: errors.length === 0 && strength !== 'Weak', strength, score, errors, suggestions: [] };
  }

  /* ── Debounce helper ─────────────────────────────────────────────────────── */
  function debounce(fn, ms) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
  }

  /* ── Initialise one field ────────────────────────────────────────────────── */
  function initField(inputEl) {
    if (inputEl.dataset.strengthInit) return;   // already initialised
    inputEl.dataset.strengthInit = '1';

    buildMeter(inputEl);

    const check = debounce(async () => {
      const pw     = inputEl.value;
      const result = pw ? await fetchStrength(pw) : { strength: 'Weak', score: 0, errors: [], suggestions: [] };
      updateUI(inputEl, result, pw);
    }, DEBOUNCE_MS);

    inputEl.addEventListener('input', check);
    inputEl.addEventListener('focus', check);   // show on focus if pre-filled
  }

  /* ── Password show/hide toggle ───────────────────────────────────────────── */
  function initToggle(toggleBtn) {
    const targetId = toggleBtn.dataset.toggleTarget;
    const target   = targetId ? document.getElementById(targetId) : null;
    if (!target) return;
    toggleBtn.addEventListener('click', () => {
      const isText = target.type === 'text';
      target.type  = isText ? 'password' : 'text';
      const icon   = toggleBtn.querySelector('i');
      if (icon) icon.className = isText ? 'bi bi-eye' : 'bi bi-eye-slash';
    });
  }

  /* ── Auto-init on DOMContentLoaded ──────────────────────────────────────── */
  function autoInit() {
    document.querySelectorAll('[data-strength-meter="true"]').forEach(initField);
    document.querySelectorAll('[data-pwd-toggle]').forEach(initToggle);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

  /* ── Public API ──────────────────────────────────────────────────────────── */
  window.PasswordStrength = { init: initField, check: fetchStrength, fallback: clientSideFallback };

}());
