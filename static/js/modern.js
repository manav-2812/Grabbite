/**
 * GrabBite Modern UI v2.0
 * Animations, skeleton loading, mobile nav, toasts,
 * scroll progress, back-to-top, lazy images, page loader
 */
(function () {
  'use strict';

  const $   = id  => document.getElementById(id);
  const qs  = (s, r = document) => r.querySelector(s);
  const qsa = (s, r = document) => [...r.querySelectorAll(s)];

  /* ── Page Loader ──────────────────────────────────────────── */
  function initPageLoader() {
    const loader = $('gb-page-loader');
    if (!loader) return;
    setTimeout(() => loader.classList.add('hidden'), 50);
  }

  /* ── Scroll Progress + Back-to-Top + Sticky Nav ──────────── */
  function initScrollFeatures() {
    const progress = $('gb-scroll-progress');
    const backTop  = $('gb-back-top');
    const navbar   = qs('.gb-navbar') || qs('header');
    function onScroll() {
      const y = window.scrollY;
      const total = document.documentElement.scrollHeight - window.innerHeight;
      if (progress) progress.style.width = (total > 0 ? (y / total) * 100 : 0) + '%';
      if (backTop)  backTop.classList.toggle('visible', y > 400);
      if (navbar)   navbar.classList.toggle('scrolled', y > 10);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    backTop && backTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }

  /* ── Reveal Animations ───────────────────────────────────── */
  function initReveal() {
    /* Auto-tag common content cards so the reveal-on-scroll effect works
       across the whole app, not just templates that opt in manually. */
    const CARD_SEL = '.gb-card, .blog-card, .restaurant-card, .offer-card, .dish-card, .featured-blog-card, .product-card';
    qsa(CARD_SEL).forEach(el => {
      if (!el.classList.contains('reveal') &&
          !el.classList.contains('reveal-left') &&
          !el.classList.contains('reveal-right')) {
        el.classList.add('reveal');
      }
    });

    const io = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
    }, { threshold: 0.10, rootMargin: '0px 0px -40px 0px' });
    qsa('.reveal').forEach(el => io.observe(el));
  }

  /* ── Lazy Image Fade-in ──────────────────────────────────── */
  function initLazyImages() {
    const io = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const img = e.target;
          img.addEventListener('load',  () => img.classList.add('loaded'));
          img.addEventListener('error', () => img.classList.add('loaded'));
          if (img.complete) img.classList.add('loaded');
          io.unobserve(img);
        }
      });
    }, { rootMargin: '200px' });
    qsa('img[loading="lazy"]').forEach(img => io.observe(img));
  }

  /* ── Mobile Drawer ───────────────────────────────────────── */
  function initMobileDrawer() {
    const btn     = $('gb-hamburger');
    const drawer  = $('gb-mobile-drawer');
    const overlay = $('gb-drawer-overlay');
    const close   = $('gb-drawer-close');
    if (!btn || !drawer) return;

    const open  = () => { drawer.classList.add('open'); overlay && overlay.classList.add('open'); document.body.style.overflow = 'hidden'; };
    const close_ = () => { drawer.classList.remove('open'); overlay && overlay.classList.remove('open'); document.body.style.overflow = ''; };

    btn.addEventListener('click', open);
    close  && close.addEventListener('click', close_);
    overlay && overlay.addEventListener('click', close_);
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && drawer.classList.contains('open')) close_(); });

    const path = window.location.pathname;
    qsa('.gb-drawer-link', drawer).forEach(link => {
      const href = link.getAttribute('href') || '';
      if ((href === '/' && path === '/') || (href !== '/' && href && path.startsWith(href))) link.classList.add('active');
    });
  }

  /* ── Active Nav Links ────────────────────────────────────── */
  function initActiveNav() {
    const path = window.location.pathname;
    qsa('.gb-nav-link').forEach(link => {
      const href = link.getAttribute('href') || '';
      if (!href || href === '#') return;
      if ((href === '/' && path === '/') || (href !== '/' && path.startsWith(href))) link.classList.add('active');
    });
  }

  /* ── Bottom Nav ──────────────────────────────────────────── */
  function initBottomNav() {
    const path = window.location.pathname;
    qsa('.gb-bottom-nav-item').forEach(item => {
      const href = item.getAttribute('href') || '';
      if (!href || href === '#') return;
      if ((href === '/' && path === '/') || (href !== '/' && path.startsWith(href))) item.classList.add('active');
    });
    function syncBadge() {
      const top = $('cart-badge');
      const bot = $('gb-bottom-cart-badge');
      if (!bot) return;
      const n = top ? (parseInt(top.textContent) || 0) : 0;
      bot.textContent = n; bot.classList.toggle('show', n > 0);
    }
    const top = $('cart-badge');
    if (top) new MutationObserver(syncBadge).observe(top, { childList: true, attributes: true, subtree: true });
    syncBadge();
  }

  /* ── Theme Toggle ───────────────────────────────────────── */
  const GbTheme = {
    toggle() {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      const next = dark ? 'light' : 'dark';
      const root = document.documentElement;
      /* Enable the cross-fade only for the duration of the switch. */
      root.classList.add('gb-theme-transition');
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('gb-theme', next); } catch (e) {}
      this.sync();
      window.dispatchEvent(new CustomEvent('gb-theme-change'));
      setTimeout(() => root.classList.remove('gb-theme-transition'), 360);
    },
    sync() {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      document.querySelectorAll('#gb-theme-toggle, #profile-theme-toggle').forEach(btn => {
        const icon = btn.querySelector('i');
        if (icon) icon.className = dark ? 'fas fa-sun' : 'fas fa-moon';
        btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
        const label = btn.querySelector('.gb-theme-label');
        if (label) label.textContent = dark ? 'Light' : 'Dark';
      });
    }
  };
  window.GbTheme = GbTheme;

  function initThemeToggle() {
    GbTheme.sync();
    document.querySelectorAll('#gb-theme-toggle, #profile-theme-toggle').forEach(btn => {
      btn.addEventListener('click', () => GbTheme.toggle());
    });
    window.addEventListener('gb-theme-change', () => GbTheme.sync());
  }

  /* ── Toast System ────────────────────────────────────────── */
  function initToasts() {
    const icons = {
      success: { i: 'fa-check-circle',         c: '#16a34a' },
      error:   { i: 'fa-times-circle',          c: '#dc2626' },
      warning: { i: 'fa-exclamation-triangle',  c: '#d97706' },
      info:    { i: 'fa-info-circle',           c: '#2563eb' },
    };
    window.gbToast = function(message, type = 'info', title = null) {
      let zone = $('gb-toast-zone');
      if (!zone) { zone = document.createElement('div'); zone.id = 'gb-toast-zone'; document.body.appendChild(zone); }
      const m = icons[type] || icons.info;
      const t = document.createElement('div');
      t.className = `gb-toast ${type}`;
      t.innerHTML = `<i class="fas ${m.i} gb-toast-icon" style="color:${m.c}"></i>
        <div class="gb-toast-body">${title ? `<p class="gb-toast-title">${title}</p>` : ''}<p class="gb-toast-msg">${message}</p></div>
        <button class="gb-toast-close">&#x2715;</button>`;
      qs('.gb-toast-close', t).addEventListener('click', () => rm(t));
      zone.appendChild(t);
      const timer = setTimeout(() => rm(t), 5000);
      function rm(el) { clearTimeout(timer); el.classList.add('removing'); setTimeout(() => el.remove(), 300); }
    };
    window.showToast = (msg, type) => window.gbToast(msg, type === 'error' ? 'error' : (type || 'info'));
  }

  /* ── Favorite Button Toggle ──────────────────────────────── */
  function initFavorites() {
    document.addEventListener('click', e => {
      const btn = e.target.closest('.favorite-btn');
      if (!btn) return;
      e.preventDefault(); e.stopPropagation();
      const active = btn.classList.toggle('active');
      const icon = btn.querySelector('i');
      if (icon) icon.className = active ? 'fas fa-heart' : 'far fa-heart';
    });
  }

  /* ── Ripple Effect ───────────────────────────────────────── */
  function initRipple() {
    document.addEventListener('click', e => {
      const el = e.target.closest('.btn');
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height) * 2;
      const r = document.createElement('span');
      r.style.cssText = `position:absolute;border-radius:50%;pointer-events:none;width:${size}px;height:${size}px;left:${e.clientX - rect.left - size/2}px;top:${e.clientY - rect.top - size/2}px;background:rgba(255,255,255,.35);transform:scale(0);animation:rippleAnim .55s ease-out forwards;`;
      el.style.position = el.style.position || 'relative';
      el.style.overflow = 'hidden';
      el.appendChild(r);
      r.addEventListener('animationend', () => r.remove());
    });
    const s = document.createElement('style');
    s.textContent = '@keyframes rippleAnim{to{transform:scale(1);opacity:0;}}';
    document.head.appendChild(s);
  }

  /* ── Newsletter ──────────────────────────────────────────── */
  function initNewsletter() {
    const form = $('newsletter-form');
    if (!form) return;
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const emailEl = $('newsletter-email') || qs('[type="email"]', form);
      const msgEl   = $('newsletter-msg');
      const btnText = $('nl-btn-text');
      if (!emailEl) return;
      if (btnText) btnText.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Subscribing...';
      await new Promise(r => setTimeout(r, 900));
      if (msgEl) { msgEl.style.display = 'block'; msgEl.textContent = '🎉 Subscribed! Check your inbox.'; }
      if (btnText) btnText.innerHTML = '<i class="fas fa-check me-1"></i>Subscribed';
      emailEl.value = '';
      window.gbToast && window.gbToast('Subscribed successfully!', 'success', 'Newsletter');
    });
  }

  /* ── Init ────────────────────────────────────────────────── */
  function init() {
    initPageLoader();
    initScrollFeatures();
    initReveal();
    initLazyImages();
    initMobileDrawer();
    initActiveNav();
    initBottomNav();
    initThemeToggle();
    initToasts();
    initFavorites();
    initRipple();
    initNewsletter();
  }

  document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', init)
    : init();

})();
