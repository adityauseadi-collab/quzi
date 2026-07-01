/**
 * QuizMaster Pro — Notification Bell
 * Polls /notifications/unread-count every 30s and renders the dropdown.
 */
(function () {
  'use strict';

  const bell     = document.getElementById('notifBell');
  const dropdown = document.getElementById('notifDropdown');
  const badge    = document.getElementById('notifCount');
  const list     = document.getElementById('notifList');
  const markAll  = document.getElementById('markAllRead');

  if (!bell) return;   // not on an authenticated page

  // ── Toggle dropdown ──────────────────────────────────────────────────────
  bell.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('d-none');
    if (!dropdown.classList.contains('d-none')) loadNotifications();
  });

  document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target) && e.target !== bell) {
      dropdown.classList.add('d-none');
    }
  });

  // ── Load notification list ───────────────────────────────────────────────
  async function loadNotifications() {
    try {
      const res  = await fetch('/notifications/');
      const data = await res.json();
      renderList(data);
    } catch (e) { /* ignore */ }
  }

  function renderList(notifications) {
    if (!notifications.length) {
      list.innerHTML = '<div class="text-center text-muted py-4 small">No notifications yet</div>';
      return;
    }
    list.innerHTML = notifications.slice(0, 10).map(n => `
      <a class="notif-item ${n.is_read ? '' : 'unread'}"
         href="${n.link || '#'}"
         onclick="markRead(${n.id}, this)">
        <div class="notif-dot ${n.is_read ? 'read' : n.category}"></div>
        <div class="flex-1">
          <div class="notif-title">${escHtml(n.title)}</div>
          ${n.body ? `<div class="notif-body">${escHtml(n.body.substring(0, 80))}</div>` : ''}
          <div class="notif-time">${n.time_ago}</div>
        </div>
      </a>`).join('');
  }

  // ── Mark single read ─────────────────────────────────────────────────────
  window.markRead = async function(id, el) {
    try {
      await fetch(`/notifications/${id}/read`, { method: 'POST',
        headers: { 'X-CSRFToken': getCSRF() } });
      el.classList.remove('unread');
      el.querySelector('.notif-dot')?.classList.replace(
        ...['info','success','warning','danger'].map(c => c), 'read'
      );
      updateBadge();
    } catch (e) { /* ignore */ }
  };

  // ── Mark all read ────────────────────────────────────────────────────────
  markAll?.addEventListener('click', async () => {
    try {
      await fetch('/notifications/mark-all-read', { method: 'POST',
        headers: { 'X-CSRFToken': getCSRF() } });
      badge.classList.add('d-none');
      document.querySelectorAll('.notif-item.unread').forEach(el => {
        el.classList.remove('unread');
        el.querySelector('.notif-dot')?.setAttribute('class', 'notif-dot read');
      });
    } catch (e) { /* ignore */ }
  });

  // ── Poll unread count ────────────────────────────────────────────────────
  async function updateBadge() {
    try {
      const res  = await fetch('/notifications/unread-count');
      const data = await res.json();
      const count = data.count || 0;
      if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('d-none');
      } else {
        badge.classList.add('d-none');
      }
    } catch (e) { /* ignore */ }
  }

  // ── CSRF helper ──────────────────────────────────────────────────────────
  function getCSRF() {
    return document.querySelector('meta[name="csrf-token"]')?.content
        || document.querySelector('input[name="csrf_token"]')?.value
        || '';
  }

  function escHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;')
              .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Init
  updateBadge();
  setInterval(updateBadge, 30_000);

}());
