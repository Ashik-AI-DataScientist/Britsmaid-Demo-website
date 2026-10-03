/* Set this to your own same-origin backend when ready. Never place CRM tokens here. */
window.BritsmaidConfig = Object.assign({leadEndpoint: null}, window.BritsmaidConfig || {});
document.addEventListener('DOMContentLoaded', function () {
  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  var hero = document.querySelector('.home-hero');
  if (hero) {
    var frame;
    hero.addEventListener('pointermove', function (event) {
      if (reduced.matches || event.pointerType !== 'mouse') return;
      var rect = hero.getBoundingClientRect();
      var x = (event.clientX - rect.left) / rect.width - 0.5;
      var y = (event.clientY - rect.top) / rect.height - 0.5;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(function () { hero.style.setProperty('--cursor-x', x * 32 + 'px'); hero.style.setProperty('--cursor-y', y * 32 + 'px'); });
    });
    function resetMotion() { cancelAnimationFrame(frame); hero.style.setProperty('--cursor-x', '0px'); hero.style.setProperty('--cursor-y', '0px'); }
    hero.addEventListener('pointerleave', resetMotion);
    reduced.addEventListener('change', resetMotion);
  }
  document.querySelectorAll('.earnings-form').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      if (!form.reportValidity()) return;
      var data = new FormData(form);
      var input = {location: data.get('location').trim(), bedrooms: Number(data.get('bedrooms')), land_cents: Number(data.get('land_cents') || 0), amenities: data.getAll('amenities')};
      var estimate = window.BritsmaidEarnings.calculate(input);
      var result = form.parentElement.querySelector('.estimator-result');
      result.hidden = false;
      var money = function (n) { return '₹' + n.toLocaleString('en-IN'); };
      result.querySelector('.range').textContent = money(estimate.low) + ' – ' + money(estimate.high) + ' / month';
      result.querySelector('.assumptions').textContent = 'Illustrative nightly rate: ' + money(estimate.nightly) + '; 30-day month at 45–60% occupancy. Bedroom base plus amenity premiums (combined uplift capped at 45%); land uplift capped at 5%. Location is not used in this estimate.';
      var link = result.querySelector('.calculator-proposal');
      var params = new URLSearchParams({bedrooms: input.bedrooms, location: input.location, land_cents: input.land_cents, amenities: input.amenities.join(',')});
      link.href = 'partner-with-us.html?' + params.toString() + '#enquiry';
      // Keep only property scenario data in memory, never contact information in storage.
      window.BritsmaidScenario = {input: input, estimate: estimate};
    });
    form.addEventListener('input', function () { form.parentElement.querySelector('.estimator-result').hidden = true; window.BritsmaidScenario = null; });
  });
  document.querySelectorAll('.lead-form').forEach(function (form) {
    var phone = form.elements.phone;
    var email = form.elements.email;
    var method = form.elements.contact_method;
    var status = form.querySelector('.form-status');
    var download = form.querySelector('.download-enquiry');
    var draft;
    if (form.dataset.formType === 'management') {
      var params = new URLSearchParams(location.search);
      ['bedrooms', 'location', 'land_cents'].forEach(function (key) { if (params.has(key)) form.elements[key].value = params.get(key); });
      if (params.has('amenities')) form.querySelectorAll('[name="amenities"]').forEach(function (checkbox) { checkbox.checked = params.get('amenities').split(',').includes(checkbox.value); });
      try {
        if (params.has('bedrooms')) window.BritsmaidScenario = {input: {bedrooms: Number(params.get('bedrooms')), location: params.get('location'), land_cents: Number(params.get('land_cents') || 0), amenities: (params.get('amenities') || '').split(',')}, estimate: window.BritsmaidEarnings.calculate({bedrooms: Number(params.get('bedrooms')), land_cents: Number(params.get('land_cents') || 0), amenities: (params.get('amenities') || '').split(',')})};
      } catch (error) { window.BritsmaidScenario = null; }
    }
    function validateContact() {
      form.querySelectorAll('input[type="text"][required]').forEach(function (input) { input.setCustomValidity(input.value.trim() ? '' : 'Please complete this field.'); });
      phone.setCustomValidity(''); email.setCustomValidity('');
      var p = phone.value.trim(), e = email.value.trim();
      if (!p && !e) phone.setCustomValidity('Please provide a mobile number or an email address.');
      else if (p && (!/^\+?[\d\s().-]+$/.test(p) || p.replace(/\D/g, '').length < 7 || p.replace(/\D/g, '').length > 15)) phone.setCustomValidity('Please enter a valid mobile number (7–15 digits).');
      if (method.value === 'Email' && !e) email.setCustomValidity('Please provide your email address for email contact.');
      if ((method.value === 'WhatsApp' || method.value === 'Phone call') && !p) phone.setCustomValidity('Please provide a mobile number for your selected contact method.');
    }
    form.addEventListener('input', function () { validateContact(); draft = null; download.hidden = true; status.textContent = ''; });
    form.addEventListener('change', validateContact);
    form.querySelector('[type="submit"]').addEventListener('click', validateContact);
    form.addEventListener('submit', async function (event) {
      event.preventDefault(); validateContact();
      if (!form.reportValidity()) return;
      var formData = new FormData(form);
      var answers = Object.fromEntries(formData.entries());
      if (form.dataset.formType === 'management') answers.amenities = formData.getAll('amenities');
      Object.keys(answers).forEach(function (key) { if (typeof answers[key] === 'string') answers[key] = answers[key].trim(); });
      draft = {submission_id: draft ? draft.submission_id : crypto.randomUUID(), form_type: form.dataset.formType, source_page: location.pathname, submitted_at: new Date().toISOString(), consent: {accepted: true, policy: 'privacy-policy.html', captured_at: new Date().toISOString()}, answers: answers};
      // Derive the attached estimate from the actual enquiry fields so edits cannot leave a stale scenario.
      if (form.dataset.formType === 'management') {
        var input = {bedrooms: Number(answers.bedrooms), land_cents: Number(answers.land_cents || 0), location: answers.location, amenities: answers.amenities};
        try { draft.calculator = {input: input, estimate: window.BritsmaidEarnings.calculate(input)}; } catch (error) { /* Homes over 12 rooms require an individual proposal. */ }
      }
      if (!window.BritsmaidConfig.leadEndpoint) {
        status.textContent = 'Your enquiry is ready to download. It has not been sent: online submissions are not connected yet.';
        download.hidden = false; return;
      }
      var button = form.querySelector('[type="submit"]'); button.disabled = true; status.textContent = 'Sending your enquiry…';
      try {
        var response = await fetch(window.BritsmaidConfig.leadEndpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(draft)});
        if (!response.ok) throw new Error('Submission failed');
        var receipt = await response.json();
        if (!receipt.accepted || !receipt.submission_id) throw new Error('Missing confirmation');
        status.textContent = 'Thank you. Your enquiry has been received. Reference: ' + receipt.submission_id;
        form.reset(); draft = null; download.hidden = true;
      } catch (error) { status.textContent = 'We could not confirm delivery. Please download your enquiry and try again later.'; download.hidden = false; }
      finally { button.disabled = false; }
    });
    download.addEventListener('click', function () {
      if (!draft) return;
      var url = URL.createObjectURL(new Blob([JSON.stringify(draft, null, 2)], {type: 'application/json'}));
      var link = document.createElement('a'); link.href = url; link.download = 'britsmaid-' + draft.form_type + '-enquiry.json'; link.click(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });
  });
});
