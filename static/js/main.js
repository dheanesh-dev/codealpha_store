/* Lumio front-end behaviour: navigation, toasts, cart, animations. */
(function () {
  'use strict';

  /* ----- Toasts ----- */
  var stack = document.getElementById('toast-stack');

  function dismiss(toast) {
    toast.classList.add('hide');
    setTimeout(function () { toast.remove(); }, 300);
  }

  function wireToast(toast) {
    var close = toast.querySelector('.toast-close');
    if (close) close.addEventListener('click', function () { dismiss(toast); });
    setTimeout(function () { if (toast.isConnected) dismiss(toast); }, 5000);
  }

  function showToast(message, type) {
    if (!stack) return;
    var icons = { success: 'fa-circle-check', error: 'fa-circle-exclamation', info: 'fa-circle-info' };
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.setAttribute('role', 'status');
    var icon = document.createElement('i');
    icon.className = 'fa-solid ' + (icons[type] || icons.info);
    var text = document.createElement('span');
    text.textContent = message;
    var close = document.createElement('button');
    close.type = 'button';
    close.className = 'toast-close';
    close.setAttribute('aria-label', 'Dismiss');
    close.innerHTML = '&times;';
    toast.append(icon, text, close);
    stack.appendChild(toast);
    wireToast(toast);
  }

  document.querySelectorAll('.toast').forEach(wireToast);

  /* ----- Mobile navigation & dropdowns ----- */
  var navToggle = document.querySelector('.nav-toggle');
  var navLinks = document.getElementById('nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function () {
      var open = navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  document.querySelectorAll('.dropdown-toggle').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var dropdown = btn.closest('.dropdown');
      var wasOpen = dropdown.classList.contains('open');
      document.querySelectorAll('.dropdown.open').forEach(function (d) { d.classList.remove('open'); });
      if (!wasOpen) dropdown.classList.add('open');
    });
  });
  document.addEventListener('click', function () {
    document.querySelectorAll('.dropdown.open').forEach(function (d) { d.classList.remove('open'); });
  });

  /* ----- Add to cart without page reload ----- */
  function updateCartBadge(count) {
    var badge = document.getElementById('cart-count');
    if (!badge) return;
    badge.textContent = count;
    badge.hidden = !count;
  }

  document.querySelectorAll('.add-to-cart-form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var button = form.querySelector('button[type="submit"]');
      if (button) button.disabled = true;
      fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body: new FormData(form),
        credentials: 'same-origin'
      })
        .then(function (response) {
          return response.json().then(function (data) { return { status: response.status, data: data }; });
        })
        .then(function (result) {
          if (result.status === 401 && result.data.login_url) {
            window.location.href = result.data.login_url;
            return;
          }
          if (typeof result.data.count === 'number') updateCartBadge(result.data.count);
          showToast(result.data.message, result.data.ok ? 'success' : 'error');
        })
        .catch(function () { form.submit(); })
        .finally(function () { if (button) button.disabled = false; });
    });
  });

  /* ----- Quantity stepper on the product page ----- */
  document.querySelectorAll('.qty-stepper[data-max]').forEach(function (stepper) {
    var input = stepper.querySelector('input');
    var max = parseInt(stepper.dataset.max, 10) || 1;
    stepper.querySelectorAll('.qty-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var value = (parseInt(input.value, 10) || 1) + parseInt(btn.dataset.step, 10);
        input.value = Math.min(Math.max(value, 1), max);
      });
    });
    input.addEventListener('change', function () {
      var value = parseInt(input.value, 10) || 1;
      input.value = Math.min(Math.max(value, 1), max);
    });
  });

  /* ----- Confirm dangerous actions ----- */
  document.querySelectorAll('form[data-confirm]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!window.confirm(form.dataset.confirm)) e.preventDefault();
    });
  });

  /* ----- Auto-submit filter forms ----- */
  document.querySelectorAll('[data-autosubmit]').forEach(function (el) {
    el.addEventListener('change', function () { el.form.submit(); });
  });
  var filterForm = document.getElementById('filter-form');
  if (filterForm) {
    ['category', 'sort'].forEach(function (name) {
      var el = filterForm.elements[name];
      if (el) el.addEventListener('change', function () { filterForm.submit(); });
    });
  }

  /* ----- Scroll reveal animation ----- */
  var items = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    items.forEach(function (el) { observer.observe(el); });
  } else {
    items.forEach(function (el) { el.classList.add('visible'); });
  }
})();

/* ----- Dashboard sidebar toggle (mobile) ----- */
(function () {
  var button = document.querySelector('.dash-menu-btn');
  var side = document.querySelector('.dash-side');
  if (!button || !side) return;
  button.addEventListener('click', function (e) { e.stopPropagation(); side.classList.toggle('open'); });
  document.addEventListener('click', function (e) {
    if (side.classList.contains('open') && !side.contains(e.target)) side.classList.remove('open');
  });
})();
