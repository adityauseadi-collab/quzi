/* QuizMaster Pro - Main JS */

// ─── DARK MODE ────────────────────────────────────────────
const html = document.documentElement;
const darkIcon = document.getElementById('darkModeIcon');

function setTheme(dark) {
  html.setAttribute('data-theme', dark ? 'dark' : 'light');
  localStorage.setItem('qm-theme', dark ? 'dark' : 'light');
  if (darkIcon) {
    darkIcon.className = dark ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  }
}

// Init theme
const savedTheme = localStorage.getItem('qm-theme');
setTheme(savedTheme === 'dark');

document.getElementById('darkModeToggle')?.addEventListener('click', () => {
  setTheme(html.getAttribute('data-theme') !== 'dark');
});

// ─── SIDEBAR TOGGLE ───────────────────────────────────────
const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('mainContent');
const sidebarToggle = document.getElementById('sidebarToggle');

sidebarToggle?.addEventListener('click', () => {
  if (window.innerWidth <= 768) {
    sidebar?.classList.toggle('open');
  } else {
    sidebar?.classList.toggle('collapsed');
    mainContent?.classList.toggle('collapsed');
  }
});

// Close sidebar on mobile when clicking outside
document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768 && sidebar?.classList.contains('open')) {
    if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
      sidebar.classList.remove('open');
    }
  }
});

// ─── AUTO DISMISS ALERTS ──────────────────────────────────
setTimeout(() => {
  document.querySelectorAll('.alert.fade').forEach(el => {
    const bsAlert = bootstrap.Alert.getInstance(el) || new bootstrap.Alert(el);
    bsAlert.close();
  });
}, 5000);

// ─── CONFIRM DELETES ──────────────────────────────────────
document.querySelectorAll('[data-confirm]').forEach(btn => {
  btn.addEventListener('click', (e) => {
    if (!confirm(btn.dataset.confirm || 'Are you sure?')) {
      e.preventDefault();
    }
  });
});

// ─── QUIZ TIMER ───────────────────────────────────────────
function initQuizTimer(minutes, onExpire) {
  const timerEl = document.getElementById('quizTimer');
  if (!timerEl || !minutes) return;

  let totalSeconds = minutes * 60;

  function update() {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    timerEl.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;

    timerEl.className = 'quiz-timer';
    if (totalSeconds <= 60) timerEl.classList.add('danger');
    else if (totalSeconds <= 300) timerEl.classList.add('warning');

    if (totalSeconds <= 0) {
      clearInterval(interval);
      onExpire?.();
      return;
    }
    totalSeconds--;
  }

  update();
  const interval = setInterval(update, 1000);
  return interval;
}

// ─── OPTION SELECTION ─────────────────────────────────────
document.querySelectorAll('.option-label').forEach(label => {
  label.addEventListener('click', () => {
    const name = label.querySelector('input')?.name;
    document.querySelectorAll(`.option-label input[name="${name}"]`).forEach(inp => {
      inp.closest('.option-label')?.classList.remove('selected');
    });
    label.classList.add('selected');
    label.querySelector('input').checked = true;

    // Update nav dot
    const qId = label.querySelector('input')?.dataset.qid;
    if (qId) {
      document.querySelector(`.q-nav-dot[data-qid="${qId}"]`)?.classList.add('answered');
    }
  });
});

// ─── QUESTION NAVIGATION (SPA mode) ──────────────────────
let currentQ = 0;
const questions = document.querySelectorAll('.question-slide');

function showQuestion(idx) {
  questions.forEach((q, i) => {
    q.style.display = i === idx ? 'block' : 'none';
  });
  document.querySelectorAll('.q-nav-dot').forEach((dot, i) => {
    dot.classList.toggle('current', i === idx);
  });
  document.getElementById('prevBtn')?.toggleAttribute('disabled', idx === 0);
  document.getElementById('nextBtn')?.toggleAttribute('disabled', idx === questions.length - 1);
  document.getElementById('submitBtn')?.classList.toggle('d-none', idx !== questions.length - 1);
  document.getElementById('nextBtn')?.classList.toggle('d-none', idx === questions.length - 1);

  // Progress
  const pct = Math.round(((idx + 1) / questions.length) * 100);
  const bar = document.getElementById('progressBar');
  if (bar) { bar.style.width = pct + '%'; bar.textContent = `${idx+1}/${questions.length}`; }
}

if (questions.length > 0) {
  showQuestion(0);
  document.getElementById('prevBtn')?.addEventListener('click', () => { if (currentQ > 0) showQuestion(--currentQ); });
  document.getElementById('nextBtn')?.addEventListener('click', () => { if (currentQ < questions.length - 1) showQuestion(++currentQ); });
  document.querySelectorAll('.q-nav-dot').forEach((dot, i) => {
    dot.addEventListener('click', () => { currentQ = i; showQuestion(i); });
  });
}

// ─── QUIZ SUBMIT WITH TIME ────────────────────────────────
let quizStartTime = Date.now();
document.getElementById('quizForm')?.addEventListener('submit', (e) => {
  const timeTaken = Math.round((Date.now() - quizStartTime) / 1000);
  let inp = document.getElementById('timeTakenInput');
  if (!inp) {
    inp = document.createElement('input');
    inp.type = 'hidden';
    inp.name = 'time_taken';
    inp.id = 'timeTakenInput';
    e.target.appendChild(inp);
  }
  inp.value = timeTaken;
});

// ─── FILE UPLOAD PREVIEW ──────────────────────────────────
const fileInput = document.getElementById('fileInput');
const fileLabel = document.getElementById('fileLabel');
fileInput?.addEventListener('change', () => {
  if (fileInput.files[0]) {
    fileLabel.textContent = fileInput.files[0].name;
    fileLabel.classList.add('text-primary');
  }
});

// ─── ANIMATE IN ───────────────────────────────────────────
document.querySelectorAll('.animate-in').forEach((el, i) => {
  el.style.opacity = '0';
  setTimeout(() => {
    el.style.animation = `fadeInUp 0.4s ease ${i * 0.05}s forwards`;
  }, 10);
});

// ─── EXPOSE GLOBALS ───────────────────────────────────────
window.QM = { initQuizTimer };
