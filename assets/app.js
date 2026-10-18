(() => {
  'use strict';
  const favKey = 'agentlab:bookmarks:v1';
  const getFavorites = () => { try { const x = JSON.parse(localStorage.getItem(favKey) || '[]'); return Array.isArray(x) ? x : []; } catch { return []; } };
  const setFavorites = x => { try { localStorage.setItem(favKey, JSON.stringify(x)); } catch {} };
  function refreshSavedButtons() {
    const fav = new Set(getFavorites());
    document.querySelectorAll('[data-save]').forEach(button => {
      const yes = fav.has(button.dataset.save);
      button.classList.toggle('saved', yes);
      button.setAttribute('aria-pressed', String(yes));
      button.setAttribute('aria-label', `${yes ? 'Remove' : 'Save'} ${button.dataset.title || 'guide'} ${yes ? 'from' : 'to'} bookmarks`);
      button.textContent = yes ? '♥ Saved' : '♡ Save';
    });
  }
  document.addEventListener('click', event => {
    const save = event.target.closest('[data-save]');
    if (save) {
      event.preventDefault();
      let favs = getFavorites();
      favs = favs.includes(save.dataset.save) ? favs.filter(s => s !== save.dataset.save) : [...favs, save.dataset.save];
      setFavorites(favs);
      refreshSavedButtons();
      window.dispatchEvent(new Event('agentlab:bookmarks'));
    }
    const copy = event.target.closest('[data-copy]');
    if (copy) {
      navigator.clipboard?.writeText(copy.dataset.copy || location.href).then(() => {
        const old = copy.textContent; copy.textContent = 'Copied ✓';
        setTimeout(() => copy.textContent = old, 1800);
      });
    }
  });
  refreshSavedButtons();
  const toggle = document.getElementById('menu-toggle');
  const nav = document.getElementById('site-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', () => {
      const isOpen = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(isOpen));
      toggle.textContent = isOpen ? 'Close ✕' : 'Menu ☰';
    });
  }
  const directory = document.querySelector('[data-directory]');
  if (directory) {
    const cards = [...directory.querySelectorAll('[data-card]')];
    const search = document.getElementById('directory-search');
    const difficulty = document.getElementById('difficulty-filter');
    const chips = [...document.querySelectorAll('[data-category]')];
    const count = document.getElementById('result-count');
    const empty = document.getElementById('directory-empty');
    const savedFilter = document.getElementById('saved-only');
    const params = new URLSearchParams(location.search);
    if (params.has('q')) search.value = params.get('q').slice(0, 100);
    let currentCategory = params.get('category') || 'All';
    if (!chips.find(chip => chip.dataset.category === currentCategory)) currentCategory = 'All';
    const filter = () => {
      const q = search.value.toLowerCase().trim();
      const d = difficulty.value;
      const fav = new Set(getFavorites());
      let found = 0;
      cards.forEach(card => {
        const match = (!q || card.dataset.search.includes(q)) && (currentCategory === 'All' || card.dataset.cat === currentCategory) && (!d || card.dataset.difficulty === d) && (!savedFilter.checked || fav.has(card.dataset.id));
        card.classList.toggle('hidden', !match);
        if (match) found++;
      });
      count.textContent = String(found);
      empty.classList.toggle('hidden', !!found);
      chips.forEach(chip => {
        const active = chip.dataset.category === currentCategory;
        chip.classList.toggle('active', active);
        chip.setAttribute('aria-pressed', String(active));
      });
      const url = new URL(location.href);
      if (q) url.searchParams.set('q', search.value); else url.searchParams.delete('q');
      if (currentCategory !== 'All') url.searchParams.set('category', currentCategory); else url.searchParams.delete('category');
      if (location.protocol === 'http:' || location.protocol === 'https:') history.replaceState(null, '', url.pathname + url.search);
    };
    chips.forEach(chip => chip.addEventListener('click', () => { currentCategory = chip.dataset.category; filter(); }));
    [search, difficulty, savedFilter].forEach(el => el.addEventListener(el === search ? 'input' : 'change', filter));
    window.addEventListener('agentlab:bookmarks', filter);
    filter();
  }
  const inquiryForms = [...document.querySelectorAll('form[data-inquiry]')];
  if (inquiryForms.length) {
    let turnstileScriptPromise;
    const loadTurnstile = () => {
      if (window.turnstile) return Promise.resolve();
      if (!turnstileScriptPromise) {
        turnstileScriptPromise = new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
          script.async = true;
          script.onload = () => window.turnstile ? resolve() : reject(new Error('Security verification could not load.'));
          script.onerror = () => reject(new Error('Security verification was blocked. Please try another browser.'));
          document.head.appendChild(script);
        });
      }
      return turnstileScriptPromise;
    };
    const loadConfig = async () => {
      const response = await fetch('/api/turnstile-config', {cache:'no-store'});
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.siteKey) throw new Error(data.error || 'Security verification is unavailable.');
      return data.siteKey;
    };
    const configPromise = loadConfig();
    inquiryForms.forEach(form => {
      const button = form.querySelector('button[type=submit]');
      const status = form.querySelector('[data-status]');
      const challengeHost = document.createElement('div');
      challengeHost.style.margin = '16px 0';
      challengeHost.setAttribute('aria-label', 'Security verification');
      const note = form.querySelector('.form-note');
      if (note) note.after(challengeHost); else button.before(challengeHost);
      let widgetId = null;
      button.disabled = true;
      status.className = 'form-status';
      status.textContent = 'Loading security verification…';
      Promise.all([configPromise,loadTurnstile()]).then(([sitekey]) => {
        widgetId = window.turnstile.render(challengeHost, {
          sitekey,
          theme:'dark',
          action:'agent_lab_inquiry',
          'expired-callback': () => {
            status.className = 'form-status error';
            status.textContent = 'Security verification expired. Please complete it again.';
          }
        });
        button.disabled = false;
        status.textContent = '';
      }).catch(error => {
        status.className = 'form-status error';
        status.textContent = error.message;
        button.disabled = true;
      });
      form.addEventListener('submit', async event => {
        event.preventDefault();
        if (!form.reportValidity()) return;
        const token = widgetId !== null && window.turnstile?.getResponse(widgetId);
        if (!token) {
          status.className = 'form-status error';
          status.textContent = 'Please complete security verification before sending.';
          return;
        }
        const fd = new FormData(form);
        const values = Object.fromEntries(fd.entries());
        values.turnstileToken = token;
        button.disabled = true;
        button.textContent = 'Sending…';
        status.className = 'form-status';
        status.textContent = '';
        try {
          const response = await fetch('/api/inquiry', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(values) });
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) throw new Error(payload.error || 'The inquiry could not be delivered.');
          status.textContent = 'Your inquiry was sent. Thank you — we will review it.';
          status.className = 'form-status success';
          form.reset();
        } catch (error) {
          status.textContent = `${error.message} You can copy your message and keep it for later. No submission was saved.`;
          status.className = 'form-status error';
          const copy = form.querySelector('[data-copy-inquiry]');
          if (copy) {
            copy.classList.remove('hidden');
            copy.onclick = () => {
              const message = [`Name: ${values.name || ''}`, `Email: ${values.email || ''}`, `Company: ${values.company || ''}`, `Interest: ${values.interest || ''}`, `Message: ${values.message || ''}`].join('\n');
              if (navigator.clipboard?.writeText) navigator.clipboard.writeText(message).then(() => { copy.textContent = 'Copied ✓'; });
              else window.prompt('Copy your inquiry', message);
            };
          }
        } finally {
          try { if (widgetId !== null) window.turnstile?.reset(widgetId); } catch {}
          button.disabled = false;
          button.textContent = 'Send inquiry →';
        }
      });
    });
  }
})();
