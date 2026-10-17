'use strict';
document.addEventListener('DOMContentLoaded',function(){
  const feedback=document.querySelector('#visitor-feedback'), booking=document.querySelector('.booking-enquiry[data-managed-booking="true"]');
  async function submit(url,payload){
    const auth=await fetch('/api/public-session',{cache:'no-store'});if(!auth.ok)throw new Error('Unable to start a secure request. Please refresh and retry.');
    const {csrf}=await auth.json();
    const multipart=payload instanceof FormData;
    const response=await fetch(url,{method:'POST',headers:{...(!multipart?{'Content-Type':'application/json'}:{}),'X-CSRF-Token':csrf},body:multipart?payload:JSON.stringify(payload)});
    let result;try{result=await response.json();}catch(error){throw new Error('We could not confirm delivery. Please contact Britsmaid directly.');}
    if(!response.ok||!result.accepted)throw new Error(result.error||'Please check your details and try again.');return result;
  }
  if(feedback){
    let requestId=crypto.randomUUID();const output=feedback.querySelector('.feedback-status');
    feedback.addEventListener('input',()=>{requestId=crypto.randomUUID();output.textContent='';});
    feedback.addEventListener('submit',async event=>{
      event.preventDefault();if(!feedback.reportValidity())return;const button=feedback.querySelector('[type=submit]');button.disabled=true;output.classList.remove('error');output.textContent='Sending your feedback…';
      const d=new FormData(feedback),payload={request_id:requestId,name:d.get('name').trim(),quote:d.get('quote').trim(),email:d.get('email').trim(),property_id:d.get('property_id'),experience_type:d.get('experience_type'),publish_permission:feedback.elements.publish_permission.checked,consent:feedback.elements.consent.checked,website_url:d.get('website_url')};
      try{const receipt=await submit('/api/feedback',payload);feedback.reset();requestId=crypto.randomUUID();output.textContent='Thank you. Your feedback has reached our team for review. It is not published automatically. Reference: '+receipt.reference;}
      catch(error){output.classList.add('error');output.textContent=error.message;}finally{button.disabled=false;}
    });
  }
  if(booking){
    const output=booking.querySelector('.booking-status'),checkIn=booking.elements.check_in,checkOut=booking.elements.check_out;
    let requestId=crypto.randomUUID(),availability=null,savedReference=null;
    const localDay=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    const today=localDay,plusDay=value=>{const d=new Date(value+'T12:00:00');d.setDate(d.getDate()+1);return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');};
    checkIn.min=today;checkOut.min=today;
    const shares=document.createElement('div');shares.className='booking-sharing';shares.hidden=true;output.after(shares);
    function validate(){
      checkOut.setCustomValidity('');booking.elements.phone.setCustomValidity('');
      if(!booking.elements.phone.value.trim()&&!booking.elements.email.value.trim())booking.elements.phone.setCustomValidity('Please provide a mobile number or email address.');
      checkOut.min=checkIn.value?plusDay(checkIn.value):today;
      if(checkIn.value&&checkOut.value&&checkOut.value<=checkIn.value)checkOut.setCustomValidity('Check-out must be after check-in.');
      if(checkIn.value&&checkOut.value&&availability?.blocks.some(x=>x.start<checkOut.value&&x.end>checkIn.value))checkOut.setCustomValidity('These dates include an unavailable night. Please select different dates.');
    }
    booking.addEventListener('input',()=>{validate();requestId=crypto.randomUUID();savedReference=null;shares.hidden=true;output.textContent='';});
    booking.querySelectorAll('[type=submit]').forEach(b=>b.addEventListener('click',validate));
    booking.addEventListener('submit',async event=>{
      event.preventDefault();validate();if(!booking.reportValidity())return;
      const channel=event.submitter?.value==='email'?'email':'whatsapp';
      const data=new FormData(booking),payload={request_id:requestId,property_id:booking.dataset.propertyId,name:data.get('guest_name').trim(),phone:data.get('phone').trim(),email:data.get('email').trim(),check_in:data.get('check_in'),check_out:data.get('check_out'),guests:data.get('guests'),notes:data.get('notes').trim(),consent:booking.elements.consent.checked,website_url:data.get('website_url')};
      const registration=window.BritsmaidGuestRegistration?.read()||{guests:[],files:[]};payload.guest_manifest=registration.guests;payload.id_consent=booking.elements.id_consent?.checked||false;payload.guardian_consent=booking.elements.guardian_consent?.checked||false;
      let body=payload;if(registration.guests.length){body=new FormData();body.append('payload',JSON.stringify(payload));for(const [key,file] of registration.files)body.append(key,file);}
      const buttons=Array.from(booking.querySelectorAll('[type=submit]'));buttons.forEach(x=>x.disabled=true);output.classList.remove('error');output.textContent='Saving your booking enquiry…';
      try{
        const receipt=await submit('/api/bookings',body);savedReference=receipt.reference;
        const message=['Hello Britsmaid, I would like to enquire about a stay.','','Reference: '+receipt.reference,'Property: '+booking.dataset.property,'Check-in: '+payload.check_in,'Check-out: '+payload.check_out,'Guests: '+payload.guests,'Name: '+payload.name,'Phone: '+(payload.phone||'Not provided'),'Email: '+(payload.email||'Not provided'),'Notes: '+(payload.notes||'None'),'','Please confirm availability, the total price, cancellation terms and the payment link.'].join('\n');
        shares.replaceChildren();
        for(const kind of [channel,channel==='email'?'whatsapp':'email']){
          const link=document.createElement('a');link.className=kind===channel?'btn-primary':'btn-secondary';
          link.textContent=kind==='email'?'Continue in your email app ↗':'Continue in WhatsApp ↗';
          link.href=kind==='email'?'mailto:'+((window.BritsmaidContact||{}).email||'contact@britsmaid.in')+'?subject='+encodeURIComponent('Booking enquiry '+receipt.reference+' — '+booking.dataset.property)+'&body='+encodeURIComponent(message):'https://wa.me/'+((window.BritsmaidContact||{}).whatsapp||'919747083777')+'?text='+encodeURIComponent(message);
          if(kind==='whatsapp'){link.target='_blank';link.rel='noopener noreferrer';}shares.append(link);
        }
        shares.hidden=false;output.textContent='Your enquiry is saved. Reference: '+receipt.reference+'. Continue below and press Send in your app. Your booking is not confirmed and no payment has been taken.';
      }catch(error){output.classList.add('error');output.textContent=error.message;}
      finally{buttons.forEach(x=>x.disabled=false);}
    });
    const panel=document.querySelector('#availability-calendar');let month=new Date(today+'T12:00:00');month=new Date(month.getFullYear(),month.getMonth(),1);
    function draw(){
      if(!panel)return;panel.querySelector('.calendar-month').textContent=month.toLocaleDateString('en-GB',{month:'long',year:'numeric'});
      const grid=panel.querySelector('.availability-grid');grid.replaceChildren();
      for(const d of ['M','T','W','T','F','S','S']){const label=document.createElement('span');label.className='weekday';label.textContent=d;grid.append(label);}
      const pad=(month.getDay()+6)%7;for(let i=0;i<pad;i++){const blank=document.createElement('span');blank.className='day empty';grid.append(blank);}
      const count=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
      for(let day=1;day<=count;day++){
        const key=[month.getFullYear(),String(month.getMonth()+1).padStart(2,'0'),String(day).padStart(2,'0')].join('-');const blocked=availability?.blocks.some(x=>x.start<=key&&x.end>key);
        const cell=document.createElement('span');cell.className='day'+(key<today?' past':blocked?' blocked':'');cell.textContent=day;cell.setAttribute('aria-label',key+(blocked?' unavailable':key<today?' past':' no known block'));grid.append(cell);
      }
    }
    panel?.querySelectorAll('[data-month]').forEach(b=>b.addEventListener('click',()=>{month.setMonth(month.getMonth()+Number(b.dataset.month));draw();}));draw();
    fetch('/api/availability/'+encodeURIComponent(booking.dataset.propertyId),{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error();return r.json();}).then(data=>{
      availability=data;draw();validate();const state=data.calendar;
      panel.querySelector('.availability-note').textContent=!state.configured?'OTA calendars are not connected yet. No known block does not mean confirmed availability. Our team will check your dates.':state.needs_review?'Calendar updates need review. Some OTA changes may be missing; our team will verify dates before confirming.':'Imported calendars are checked periodically; OTA updates can be delayed. Our team will confirm availability. Last successful import: '+new Date(state.last_success).toLocaleString('en-IN')+'.';
    }).catch(()=>{if(panel)panel.querySelector('.availability-note').textContent='Calendar status is unavailable. Our team will check your dates manually.';});
  }
});
