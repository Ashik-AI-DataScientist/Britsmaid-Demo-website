// Britsmaid prototype — client-side only, no backend. Mobile menu, listing filters, revenue estimator.

document.addEventListener('DOMContentLoaded', function () {

  // Accessible navigation and shared animated line icons.
  var menuBtn = document.querySelector('.menu-btn');
  var navEl = document.querySelector('nav');
  if (menuBtn && navEl) {
    navEl.id = 'primary-navigation';
    menuBtn.setAttribute('aria-controls', navEl.id);
    menuBtn.setAttribute('aria-expanded', 'false');
    function closeMenu() {
      navEl.classList.remove('open');
      menuBtn.setAttribute('aria-expanded', 'false');
      menuBtn.setAttribute('aria-label', 'Open menu');
    }
    menuBtn.addEventListener('click', function () {
      var open = navEl.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', String(open));
      menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    });
    navEl.addEventListener('click', function (event) { if (event.target.closest('a')) closeMenu(); });
    document.addEventListener('keydown', function (event) { if (event.key === 'Escape') { closeMenu(); menuBtn.focus(); } });
    window.addEventListener('resize', function () { if (window.innerWidth > 860) closeMenu(); });
  }
  var page = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('nav a').forEach(function (link) {
    if (link.getAttribute('href') === page) link.setAttribute('aria-current', 'page');
  });
  var iconPaths = [
    '<path d="M3 10 12 3l9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z"/><path class="icon-detail" d="M9 21v-8h6v8"/>',
    '<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M7 3v8m10-8v8M3 12h18"/><path class="icon-detail" d="m9 16 2 2 4-4"/>',
    '<path d="M12 3 3 7v6c0 4 5 7 9 9 4-2 9-5 9-9V7Z"/><path class="icon-detail" d="m8 12 3 3 5-6"/>',
    '<path d="M4 20V4m0 16h17"/><path class="icon-detail" d="m8 15 4-5 4 2 5-7"/>',
    '<path d="M16 4a5 5 0 0 0-6 6L3 17a3 3 0 0 0 4 4l7-7a5 5 0 0 0 6-6l-4 3-3-3Z"/>',
    '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6"/><path class="icon-detail" d="m9 16 2 2 4-4"/>'
  ];
  document.querySelectorAll('.vcard, .services .item, .why-grid .item').forEach(function (card, index) {
    var icon = document.createElement('span');
    icon.className = 'feature-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.innerHTML = '<svg viewBox="0 0 24 24">' + iconPaths[index % iconPaths.length] + '</svg>';
    card.prepend(icon);
  });
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add('is-visible'); observer.unobserve(entry.target); }
      });
    }, { threshold: 0.08 });
    document.querySelectorAll('.section-head, .vcard, .services .item, .why-grid .item, .owners').forEach(function (item) {
      item.classList.add('reveal-ready'); observer.observe(item);
    });
  }
  // Listings filter (stay.html)
  var filterBar = document.querySelector('.filter-bar');
  if (filterBar) {
    var cards = Array.prototype.slice.call(document.querySelectorAll('.pcard[data-location]'));
    var countEl = document.querySelector('.results-count');
    var locationSel = document.getElementById('f-location');
    var bedroomsSel = document.getElementById('f-bedrooms');
    var guestsSel = document.getElementById('f-guests');
    var resetBtn = document.querySelector('.filter-reset');

    function applyFilters() {
      var loc = locationSel ? locationSel.value : '';
      var beds = bedroomsSel ? bedroomsSel.value : '';
      var guests = guestsSel ? guestsSel.value : '';
      var visible = 0;

      cards.forEach(function (card) {
        var matchLoc = !loc || card.dataset.location === loc;
        var matchBeds = !beds || Number(card.dataset.bedrooms) >= Number(beds);
        var matchGuests = !guests || Number(card.dataset.guests) >= Number(guests);
        var show = matchLoc && matchBeds && matchGuests;
        card.classList.toggle('hidden', !show);
        if (show) visible++;
      });

      if (countEl) countEl.textContent = visible + ' propert' + (visible === 1 ? 'y' : 'ies') + ' found';
    }

    [locationSel, bedroomsSel, guestsSel].forEach(function (el) {
      if (el) el.addEventListener('change', applyFilters);
    });
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        [locationSel, bedroomsSel, guestsSel].forEach(function (el) { if (el) el.value = ''; });
        applyFilters();
      });
    }
    applyFilters();
  }

});
