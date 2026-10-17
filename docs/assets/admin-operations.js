'use strict';
(function(){
 const $=(s,root=document)=>root.querySelector(s), studio=window.BritsmaidStudio;
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let operations={bookings:[],calendars:[]},properties=[],openedBooking=null;
 function property(id){return properties.find(p=>p.id===id);}
 async function load(){
  const [a,b]=await Promise.all([fetch('/admin/api/operations',{cache:'no-store'}),fetch('/admin/api/content',{cache:'no-store'})]);
  if(!a.ok||!b.ok)throw new Error('Unable to load booking operations. Sign in again if your session expired.');
  operations=await a.json();properties=(await b.json()).properties;renderBookings();renderCalendars();
 }
 function renderBookings(){
  const filter=$('#booking-filter').value,q=$('#booking-search').value.toLowerCase();
  const rows=operations.bookings.filter(b=>(!filter||b.status===filter)&&`${b.id} ${b.name}`.toLowerCase().includes(q));
  $('#booking-list').innerHTML=rows.map(b=>`<article class="panel booking-row"><div><p class="eyebrow">${esc(b.id)}</p><h2>${esc(property(b.property_id)?.name||'Property')}</h2><p><strong>${esc(b.name)}</strong> · ${esc(b.check_in)} → ${esc(b.check_out)} · ${b.guests} guests</p><p class="muted">${esc(b.email||b.phone)}</p>${b.conflicts.length?'<p class="notice error">Dates overlap another booking or OTA block. Review before replying.</p>':''}</div><div class="booking-row-actions"><span class="badge">${esc(b.status)}</span><span class="muted">Payment: ${esc(b.payment_status.replaceAll('_',' '))}</span><button class="secondary" data-booking="${esc(b.id)}">Review request →</button></div></article>`).join('')||'<div class="empty"><h2>Ready for your next guests.</h2><p>Saved website booking requests will appear here.</p></div>';
 }
 function renderCalendars(){
  $('#calendar-list').innerHTML=operations.calendars.map(c=>`<article class="panel"><div class="title-row"><div><h2>${esc(property(c.property_id)?.name||'Property')}</h2><p class="muted">${c.summary.feed_count} enabled calendar${c.summary.feed_count===1?'':'s'} · ${!c.summary.configured?'Not connected':c.summary.needs_review?'Needs review':'Last imports up to date'}</p></div></div>${c.feeds.map(f=>`<div class="feed-row"><div><strong>${esc(f.name)}</strong><span class="badge">${f.enabled?'enabled':'disabled'}</span><p class="muted">${f.block_count} imported blocks · ${f.last_success?'Last success: '+esc(new Date(f.last_success).toLocaleString('en-IN')):'No successful import yet'}</p>${f.error?`<p class="notice error">${esc(f.error)}</p>`:''}</div><div class="feed-actions"><button class="secondary" data-edit-feed="${esc(f.id)}">Edit</button><button class="secondary" data-sync-feed="${esc(f.id)}" ${!f.enabled?'disabled':''}>Sync now ↻</button></div></div>`).join('')||'<p class="muted">Add each OTA’s private export link to see its unavailable nights here.</p>'}<div class="export-feed"><label>Website iCal export · direct confirmed bookings only<input readonly value="${esc(c.export_url)}" aria-label="iCal export for ${esc(property(c.property_id)?.name)}"></label><button class="secondary" data-copy-export="${esc(c.property_id)}">Copy export link</button><p class="muted">${c.preview?'Local preview URL only. It cannot be imported by an OTA until the website is hosted and its final domain is set.':'Import this private link into the matching listing on each OTA. Do not share it publicly.'}</p></div></article>`).join('');
 }
 function reply(b){
  const p=property(b.property_id),lines=['Hello '+b.name+',','','Booking reference: '+b.id,'Property: '+(p?.name||'Britsmaid villa'),'Check-in: '+b.check_in,'Check-out: '+b.check_out,'Guests: '+b.guests,''];
  if(b.status==='confirmed'){
   lines.push('We confirm the dates for your stay, subject to the agreed booking and payment terms.');
   if(b.amount)lines.push('Agreed total: INR '+Number(b.amount).toLocaleString('en-IN'));
   if(b.payment_status==='paid')lines.push('Your payment has been recorded as received.');
   else if(b.payment_url)lines.push('Please use this payment link: '+b.payment_url);
   else lines.push('We will share the payment instructions and booking terms separately.');
  }else if(b.status==='cancelled'||b.status==='declined')lines.push('Your booking request is '+b.status+'. Please contact us if you would like to discuss alternative dates.');
  else lines.push('Thank you for your enquiry. We are checking availability and will confirm the price and booking terms before requesting payment.');
  lines.push('','Britsmaid');return lines.join('\n');
 }
 function messageActions(b){
  const root=$('#booking-message-actions');root.replaceChildren();const message=reply(b);$('#booking-message-preview').textContent=message;
  if(b.conflicts.length&&b.status==='confirmed'){root.textContent='Resolve the calendar conflict before preparing a confirmation or payment message.';return;}
  if(b.phone){const a=document.createElement('a');a.className='primary';a.textContent='Prepare WhatsApp ↗';a.href='https://wa.me/'+b.phone.replace(/\D/g,'')+'?text='+encodeURIComponent(message);a.target='_blank';a.rel='noopener noreferrer';root.append(a);}
  if(b.email){const a=document.createElement('a');a.className='secondary';a.textContent='Prepare email ↗';a.href='mailto:'+encodeURIComponent(b.email)+'?subject='+encodeURIComponent('Your Britsmaid stay · '+b.id)+'&body='+encodeURIComponent(message);root.append(a);}
 }
 function editBooking(id){
  const b=operations.bookings.find(x=>x.id===id);if(!b)return;openedBooking=id;const form=$('#booking-management');form.reset();
  for(const key of ['id','version','status','payment_status','amount','payment_url','team_notes'])form.elements[key].value=b[key]??'';
  $('#booking-reference').textContent=b.id;$('#booking-heading').textContent=property(b.property_id)?.name||'Booking request';
  $('#booking-details').innerHTML=`<strong>${esc(b.name)}</strong><p>${esc(b.check_in)} → ${esc(b.check_out)} · ${b.guests} guests</p><p>${esc(b.phone||'No phone')}<br>${esc(b.email||'No email')}</p><p class="booking-message-preview">${esc(b.notes||'No guest notes.')}</p>`;
  window.BritsmaidBookingGuests?.render(b);
  const c=operations.calendars.find(x=>x.property_id===b.property_id);$('#booking-calendar-warning').textContent=b.conflicts.length?'Known date conflict: '+b.conflicts.map(x=>x.source+' '+x.start+' → '+x.end).join('; '):!c?.summary.configured?'OTA calendars are not connected. Check each platform manually before confirming.':c.summary.needs_review?'One or more OTA imports need review. Sync or verify the platforms directly before confirming.':'No overlap in the imported snapshot. Check the current OTA calendars before confirmation; changes can be delayed.';
  $('.editor-error',form).textContent='';messageActions(b);$('#booking-dialog').showModal();
 }
 function editCalendar(id){
  const feed=operations.calendars.flatMap(c=>c.feeds).find(f=>f.id===id),form=$('#calendar-form');form.reset();
  $('#calendar-property').innerHTML=properties.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');
  for(const key of ['id','version','name','url','property_id'])form.elements[key].value=feed?.[key]??(key==='property_id'?properties[0]?.id||'':'');
  form.elements.enabled.checked=feed?!!feed.enabled:true;form.elements.property_id.disabled=!!feed;form.elements.url.readOnly=!!feed;$('.editor-error',form).textContent='';$('#calendar-dialog').showModal();
 }
 $('#booking-search').addEventListener('input',renderBookings);$('#booking-filter').addEventListener('change',renderBookings);
 $('#booking-list').addEventListener('click',e=>{const b=e.target.closest('[data-booking]');if(b)editBooking(b.dataset.booking);});
 $('#new-calendar').addEventListener('click',()=>editCalendar());
 $('#refresh-bookings').addEventListener('click',()=>load().then(()=>studio.status('Booking requests refreshed.')).catch(e=>studio.status(e.message,true)));
 for(const id of ['close-booking','cancel-booking'])$('#'+id).addEventListener('click',()=>$('#booking-dialog').close());
 for(const id of ['close-calendar','cancel-calendar'])$('#'+id).addEventListener('click',()=>$('#calendar-dialog').close());
 $('#calendar-list').addEventListener('click',async e=>{
  const edit=e.target.closest('[data-edit-feed]');if(edit){editCalendar(edit.dataset.editFeed);return;}
  const copy=e.target.closest('[data-copy-export]');if(copy){const c=operations.calendars.find(c=>c.property_id===copy.dataset.copyExport);try{await navigator.clipboard.writeText(c.export_url);studio.status(c.preview?'Local preview export link copied. Set the hosted domain before connecting an OTA.':'Private export link copied.');}catch(error){studio.status('Select and copy the export URL from the field.',true);}return;}
  const sync=e.target.closest('[data-sync-feed]');if(sync){sync.disabled=true;studio.status('Importing calendar…');try{await studio.api('/admin/api/calendars/sync',{id:sync.dataset.syncFeed});await load();studio.status('Calendar imported. Known unavailable nights are updated.');}catch(error){await load();studio.status(error.message,true);}finally{sync.disabled=false;}}
 });
 $('#booking-management').addEventListener('input',()=>{$('#booking-message-actions').replaceChildren();$('#booking-message-preview').textContent='Save changes to prepare an updated guest message.';});
 $('#booking-management').addEventListener('submit',async e=>{
  e.preventDefault();const form=e.target,button=form.querySelector('[type=submit]');button.disabled=true;$('.editor-error',form).textContent='';
  try{const data=Object.fromEntries(new FormData(form));data.version=Number(data.version);data.availability_checked=form.elements.availability_checked.checked;await studio.api('/admin/api/bookings',data);await load();editBooking(openedBooking);$('.editor-error',form).textContent='Saved. Guest messages now reflect this booking.';}
  catch(error){$('.editor-error',form).textContent=error.message;}finally{button.disabled=false;}
 });
 $('#calendar-form').addEventListener('submit',async e=>{
  e.preventDefault();const form=e.target,button=form.querySelector('[type=submit]');button.disabled=true;$('.editor-error',form).textContent='';
  try{const d=Object.fromEntries(new FormData(form));d.property_id=form.elements.property_id.value;d.version=Number(d.version);d.enabled=form.elements.enabled.checked;await studio.api('/admin/api/calendars',d);form.closest('dialog').close();await load();studio.status('Calendar saved. Use Sync now for the first import; the running app checks periodically.');}
  catch(error){$('.editor-error',form).textContent=error.message;}finally{button.disabled=false;}
 });
 document.querySelectorAll('[data-tab="bookings"],[data-tab="calendars"]').forEach(b=>b.addEventListener('click',()=>load().catch(e=>studio.status(e.message,true))));
 load().catch(error=>studio.status(error.message,true));
 window.BritsmaidOperations={refreshBooking:async id=>{await load();editBooking(id);}};
}());
