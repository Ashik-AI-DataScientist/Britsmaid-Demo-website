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
  // The calculator and proposal handoff live in calculator-flow.js. Calculation never submits a lead.
  document.querySelectorAll('.lead-form').forEach(function (form) {
    var phone = form.elements.phone;
    var email = form.elements.email;
    var method = form.elements.contact_method;
    var status = form.querySelector('.form-status');
    var download = form.querySelector('.download-enquiry');
    var draft;
    if (window.BritsmaidConfig.leadEndpoint || window.BritsmaidConfig.appsScriptUrl) { form.querySelector('[type=submit]').textContent = 'Submit my property enquiry ↗'; form.querySelector('.note').textContent = 'Submit your answers to our team. You can also prepare a WhatsApp or email message after saving.'; }
    var shareRow = document.createElement('div');
    shareRow.className = 'enquiry-share'; shareRow.hidden = true;
    var whatsappShare = document.createElement('a'), emailShare = document.createElement('a');
    whatsappShare.className = 'btn-primary'; whatsappShare.textContent = 'Send enquiry via WhatsApp ↗'; whatsappShare.target = '_blank'; whatsappShare.rel = 'noopener noreferrer';
    emailShare.className = 'btn-secondary'; emailShare.textContent = 'Send enquiry by email ↗';
    shareRow.append(whatsappShare,emailShare); status.after(shareRow);
    function prepareShare() {
      var lines = ['Hello Britsmaid, here is my ' + draft.form_type + ' property enquiry.', ''];
      Object.keys(draft.answers).forEach(function (key) {
        var control = form.querySelector('[name="' + key + '"]');
        var label = key === 'amenities' ? 'Amenities' : key === 'consent' ? 'Consent' : control && control.labels && control.labels[0] ? control.labels[0].textContent.replace(/\s*\*$/, '').trim() : key.replace(/_/g, ' ');
        var value = draft.answers[key];
        lines.push(label + ': ' + (Array.isArray(value) ? value.join(', ') || 'None' : value || 'Not provided'));
      });
      if (draft.calculator) lines.push('Illustrative monthly gross revenue: INR ' + draft.calculator.estimate.low + '–' + draft.calculator.estimate.high + ' (not guaranteed)');
      lines.push('Enquiry reference: ' + (draft.reference||draft.submission_id));
      var message = lines.join('\n');
      whatsappShare.href = 'https://wa.me/' + ((window.BritsmaidContact || {}).whatsapp || '919747083777') + '?text=' + encodeURIComponent(message);
      emailShare.href = 'mailto:' + ((window.BritsmaidContact || {}).email || 'contact@britsmaid.in') + '?subject=' + encodeURIComponent('Britsmaid ' + draft.form_type + ' property enquiry') + '&body=' + encodeURIComponent(message);
      shareRow.hidden = false;
    }
    function validateContact() {
      form.querySelectorAll('input[type="text"][required]').forEach(function (input) { input.setCustomValidity(input.value.trim() ? '' : 'Please complete this field.'); });
      phone.setCustomValidity(''); email.setCustomValidity('');
      var p = phone.value.trim(), e = email.value.trim();
      if (!p && !e) phone.setCustomValidity('Please provide a mobile number or an email address.');
      else if (p && (!/^\+[\d\s().-]+$/.test(p) || p.replace(/\D/g, '').length < 7 || p.replace(/\D/g, '').length > 15)) phone.setCustomValidity('Include + and your country code, followed by 7–15 digits, for example +91.');
      if (method.value === 'Email' && !e) email.setCustomValidity('Please provide your email address for email contact.');
      if ((method.value === 'WhatsApp' || method.value === 'Phone call') && !p) phone.setCustomValidity('Please provide a mobile number for your selected contact method.');
    }
    var submitting=false,revision=0,savedRevision=-1;
    function changed(){revision++;validateContact();draft=null;download.hidden=true;shareRow.hidden=true;status.textContent='';}
    form.addEventListener('input',changed);
    form.addEventListener('proposal:prefilled',changed);
    form.addEventListener('change', validateContact);
    form.querySelector('[type="submit"]').addEventListener('click', validateContact);
    form.addEventListener('submit', async function (event) {
      event.preventDefault(); validateContact();
      if (submitting || !form.reportValidity()) return;
      if(savedRevision===revision&&draft){status.textContent='This enquiry is already saved. Reference: '+draft.reference;return;}
      var formData = new FormData(form);
      var answers = Object.fromEntries(formData.entries());
      if (form.dataset.formType === 'management') answers.amenities = formData.getAll('amenities');
      Object.keys(answers).forEach(function (key) { if (typeof answers[key] === 'string') answers[key] = answers[key].trim(); });
      draft = {submission_id: draft ? draft.submission_id : crypto.randomUUID(), form_type: form.dataset.formType, source_page: location.pathname, submitted_at: new Date().toISOString(), consent: {accepted: true, policy: 'privacy-policy.html', captured_at: new Date().toISOString()}, answers: answers};
      if(draft.form_type==='management'&&(form.dataset.leadSource==='calculator'||new URLSearchParams(location.search).get('source')==='tailored_proposal'))draft.form_type='proposal';
      // Derive the attached estimate from the actual enquiry fields so edits cannot leave a stale scenario.
      if (form.dataset.formType === 'management') {
        var input = {bedrooms: Number(answers.bedrooms), land_cents: Number(answers.land_cents || 0), location: answers.location, amenities: answers.amenities};
        try { draft.calculator = {input: input, estimate: window.BritsmaidEarnings.calculate(input)}; } catch (error) { /* Homes over 12 rooms require an individual proposal. */ }
      }
      if (!window.BritsmaidConfig.leadEndpoint && !window.BritsmaidConfig.appsScriptUrl) {
        prepareShare();
        status.textContent = 'Your completed enquiry is ready. It has not been sent. Choose WhatsApp or email below and press Send in your app, or download a copy.';
        download.hidden = false; return;
      }
      var button = form.querySelector('[type="submit"]'),sentDraft=draft,sentRevision=revision;submitting=true;button.disabled=true;status.textContent='Sending your enquiry…';
      try {
        var receipt;
        if (window.BritsmaidConfig.leadEndpoint && window.BritsmaidLeads) receipt=await window.BritsmaidLeads.submit(draft);
        else if (window.BritsmaidConfig.appsScriptUrl) receipt = await window.BritsmaidSheets.submit(draft);
        else {
        var response = await fetch(window.BritsmaidConfig.leadEndpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(draft)});
        if (!response.ok) throw new Error('Submission failed');
        receipt = await response.json();
        }
        if (!receipt.accepted || !receipt.submission_id) throw new Error('Missing confirmation');
        sentDraft.reference=receipt.submission_id;
        if(revision===sentRevision){savedRevision=revision;status.textContent='Thank you. Your enquiry has been received. Reference: '+receipt.submission_id;prepareShare();download.hidden=false;}
        else status.textContent='Your previous answers were saved. Reference: '+receipt.submission_id+'. Your latest edits have not been submitted.';
      } catch (error) {if(revision===sentRevision){draft=sentDraft;prepareShare();download.hidden=false;}status.textContent='Your enquiry has not been confirmed as saved. '+(error.message||'Please retry.')+' You can also use WhatsApp or email below.';}
      finally {submitting=false;button.disabled=false;}
    });
    download.addEventListener('click', function () {
      if (!draft) return;
      var url = URL.createObjectURL(new Blob([JSON.stringify(draft, null, 2)], {type: 'application/json'}));
      var link = document.createElement('a'); link.href = url; link.download = 'britsmaid-' + draft.form_type + '-enquiry.json'; link.click(); setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });
  });
});
