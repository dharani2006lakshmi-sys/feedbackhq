/* ───────────────────────────────────────────────
   main.js — Feedback App UI Enhancements
─────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', () => {

  /* ── 1. Auto-dismiss flash messages ─────────── */
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-8px)';
      setTimeout(() => el.remove(), 500);
    }, 4000);
  });

  /* ── 2 & 3. Table live search + rating filter ─ */
  const searchInput = document.getElementById('tableSearch');
  const ratingFilter = document.getElementById('ratingFilter');
  function applyTableFilters() {
    const q = searchInput ? searchInput.value.toLowerCase() : '';
    const val = ratingFilter ? ratingFilter.value : '';
    document.querySelectorAll('tbody tr').forEach(row => {
      const ratingCell = row.querySelector('.rating-val');
      const matchesText = !q || row.textContent.toLowerCase().includes(q);
      const matchesRating = !val || (ratingCell && ratingCell.dataset.rating === val);
      row.style.display = matchesText && matchesRating ? '' : 'none';
    });
  }
  if (searchInput) searchInput.addEventListener('input', applyTableFilters);
  if (ratingFilter) ratingFilter.addEventListener('change', applyTableFilters);

  /* ── 4. Render star ratings in tables ───────── */
  document.querySelectorAll('.rating-val').forEach(cell => {
    const val = parseInt(cell.textContent.trim(), 10);
    if (!isNaN(val)) {
      cell.dataset.rating = String(val);
      cell.innerHTML =
        '<span class="stars">' + '★'.repeat(val) + '<span style="opacity:0.25">' +
        '★'.repeat(5 - val) + '</span></span>';
    }
  });

  /* ── 5. Auto-colorise status badges ─────────── */
  document.querySelectorAll('.status-val').forEach(cell => {
    const txt = cell.textContent.trim().toLowerCase();
    let cls = 'badge-neutral';
    if (['positive','resolved','approved','good'].includes(txt))  cls = 'badge-positive';
    if (['negative','rejected','bad','spam'].includes(txt)) cls = 'badge-negative';
    cell.innerHTML = `<span class="badge ${cls}">${cell.textContent.trim()}</span>`;
  });

  /* ── 6. Form submission loading state ───────── */
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('button[type="submit"]');
      if (btn) {
        btn.disabled = true;
        btn.textContent = 'Please wait…';
        btn.style.opacity = '0.7';
      }
    });
  });

  /* ── 7. Password strength meter ─────────────── */
  const pwInput = document.querySelector('input[name="password"]');
  const strengthBar = document.getElementById('strengthBar');
  if (pwInput && strengthBar) {
    pwInput.addEventListener('input', () => {
      const v = pwInput.value;
      let score = 0;
      if (v.length >= 8) score++;
      if (/[A-Z]/.test(v)) score++;
      if (/[0-9]/.test(v)) score++;
      if (/[^A-Za-z0-9]/.test(v)) score++;
      const widths = ['0%','30%','55%','80%','100%'];
      const colors = ['transparent','#f87171','#fb923c','#facc15','#34d399'];
      const fill = strengthBar.querySelector('.progress-fill');
      if (fill) {
        fill.style.width  = widths[score];
        fill.style.background = colors[score];
      }
    });
  }

  /* ── 8. Animate stat counters ────────────────── */
  document.querySelectorAll('.stat-value[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const isFloat = String(target).includes('.');
    const duration = 900;
    const start = performance.now();
    const from = 0;

    function update(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = from + (target - from) * eased;
      el.textContent = isFloat ? current.toFixed(1) : Math.round(current);
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });

  /* ── 9. Confirm before leaving with unsaved form ─ */
  let formDirty = false;
  document.querySelectorAll('form input, form textarea, form select').forEach(el => {
    if (!el.closest('.auth-card')) {
      el.addEventListener('input', () => { formDirty = true; });
    }
  });
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', () => { formDirty = false; });
  });
  window.addEventListener('beforeunload', e => {
    if (formDirty) { e.preventDefault(); e.returnValue = ''; }
  });

  /* ── 10. Date input default to today ─────────── */
  const dateInput = document.querySelector('input[name="date"]');
  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }

  /* ── 11. One-click demo credentials fill ───── */
  const fillDemoBtn = document.getElementById('fillDemoBtn');
  if (fillDemoBtn) {
    fillDemoBtn.addEventListener('click', () => {
      const email = document.getElementById('email');
      const pw = document.getElementById('password');
      if (email) email.value = fillDemoBtn.dataset.email || 'user@feedbackhq.com';
      if (pw) pw.value = fillDemoBtn.dataset.password || 'user1234';
    });
  }

});