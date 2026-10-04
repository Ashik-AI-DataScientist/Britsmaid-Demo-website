document.addEventListener('DOMContentLoaded', function () {
  var form = document.querySelector('.booking-enquiry');
  if (form) {
    var checkIn = form.elements.check_in, checkOut = form.elements.check_out;
    var now = new Date();
    var today = now.getFullYear() + '-' + String(now.getMonth()+1).padStart(2,'0') + '-' + String(now.getDate()).padStart(2,'0');
    checkIn.min = today; checkOut.min = today;
    function validateDates() {
      checkOut.setCustomValidity('');
      if (checkIn.value) {
        var next = new Date(checkIn.value + 'T12:00:00'); next.setDate(next.getDate()+1);
        checkOut.min = next.getFullYear() + '-' + String(next.getMonth()+1).padStart(2,'0') + '-' + String(next.getDate()).padStart(2,'0');
      } else checkOut.min = today;
      if (checkIn.value && checkOut.value && checkOut.value <= checkIn.value) checkOut.setCustomValidity('Check-out must be after check-in.');
    }
    form.addEventListener('input', function () { validateDates(); form.querySelector('.booking-status').textContent = ''; });
    form.querySelectorAll('[type="submit"]').forEach(function (button) { button.addEventListener('click', validateDates); });
    form.addEventListener('submit', function (event) {
      event.preventDefault(); validateDates(); if (!form.reportValidity()) return;
      var data = new FormData(form);
      var pretty = function (date) { return new Date(date + 'T12:00:00').toLocaleDateString('en-GB', {day:'numeric',month:'short',year:'numeric'}); };
      var message = ['Hello Britsmaid, I would like to enquire about a stay.', '', 'Villa: ' + form.dataset.property, 'Check-in: ' + pretty(data.get('check_in')), 'Check-out: ' + pretty(data.get('check_out')), 'Guests: ' + data.get('guests'), 'Name: ' + (data.get('guest_name').trim() || 'Not provided'), 'Notes: ' + (data.get('notes').trim() || 'None'), '', 'Please confirm availability, the total price and booking terms.'].join('\n');
      var channel = event.submitter && event.submitter.value === 'email' ? 'email' : 'whatsapp';
      var href = channel === 'email' ? 'mailto:contact@britsmaid.in?subject=' + encodeURIComponent('Stay enquiry — ' + form.dataset.property) + '&body=' + encodeURIComponent(message) : 'https://wa.me/919747083777?text=' + encodeURIComponent(message);
      form.dispatchEvent(new CustomEvent('booking:prepared', {detail:{channel:channel,href:href,message:message}}));
      var link = document.createElement('a'); link.href = href;
      if (channel === 'whatsapp') { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
      document.body.appendChild(link); link.click(); link.remove();
      form.querySelector('.booking-status').textContent = 'Your enquiry message is prepared. Press Send in ' + (channel === 'email' ? 'your email app' : 'WhatsApp') + ' to deliver it. Your reservation is not confirmed yet.';
    });
  }
  var gallery = document.querySelector('.property-gallery'), dialog = document.querySelector('.photo-viewer');
  if (gallery && dialog) {
    var buttons = Array.from(gallery.querySelectorAll('.photo-tile')), selected = 0, opener;
    function show(index) {
      selected = (index + buttons.length) % buttons.length;
      var source = buttons[selected].querySelector('img'), preview = dialog.querySelector('img');
      preview.src = source.src; preview.alt = source.alt;
      dialog.querySelector('.photo-counter').textContent = (selected+1) + ' / ' + buttons.length;
    }
    function close() { dialog.close(); document.body.classList.remove('viewer-open'); if (opener) opener.focus(); }
    buttons.forEach(function (button,index) { button.addEventListener('click', function () { opener = button; show(index); dialog.showModal(); document.body.classList.add('viewer-open'); }); });
    dialog.querySelector('.photo-close').addEventListener('click',close);
    dialog.querySelector('.photo-prev').addEventListener('click',function () {show(selected-1);});
    dialog.querySelector('.photo-next').addEventListener('click',function () {show(selected+1);});
    dialog.addEventListener('cancel',function (event) {event.preventDefault();close();});
    dialog.addEventListener('keydown',function (event) {if(event.key==='ArrowRight'){event.preventDefault();show(selected+1);}if(event.key==='ArrowLeft'){event.preventDefault();show(selected-1);}});
    dialog.addEventListener('click',function (event) {if(event.target===dialog)close();});
  }
});
