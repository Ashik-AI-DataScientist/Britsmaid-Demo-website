'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 const form=document.querySelector('.booking-enquiry[data-managed-booking="true"]');if(!form)return;
 const section=document.createElement('div');section.className='guest-registration';
 section.innerHTML='<details><summary>Check-in guests & private IDs · optional now</summary><p class="note">You can send an enquiry without IDs. If you add guest registration now, include every guest. ID images are private to authorised staff and are never included in WhatsApp or email messages. JPEG, PNG or WebP, 2 MB each; under 24 MB combined.</p><label class="consent-row"><input type="checkbox" id="add-guest-registration"><span>Add guest names and ID images now</span></label><div id="guest-registration-fields" hidden><div id="guest-registration-list"></div><label class="consent-row"><input type="checkbox" name="id_consent"><span>I am 18 or older and have permission to submit these guest details and IDs for check-in review. IDs are normally removed 30 days after checkout; unconfirmed enquiries retain IDs for up to 30 days.</span></label><label class="consent-row" id="guardian-permission-row" hidden><input type="checkbox" name="guardian_consent"><span>I have the parent or legal guardian’s permission to submit each minor’s details and ID. Staff must review the relationship and guardian details before check-in.</span></label></div></details>';
 form.querySelector('[name=notes]').closest('.field').after(section);
 const toggle=section.querySelector('#add-guest-registration'),fields=section.querySelector('#guest-registration-fields'),list=section.querySelector('#guest-registration-list');
 const relationships=['Self','Spouse','Father','Mother','Son','Daughter','Brother','Sister','Grandfather','Grandmother','Grandson','Granddaughter','Uncle','Aunt','Niece','Nephew','Cousin','Friend','Legal ward','Other relative'];
 function conditions(){
  let minors=false;list.querySelectorAll('.checkin-guest').forEach(row=>{const minor=row.querySelector('[data-minor]').checked;minors=minors||minor;row.querySelector('.guardian-fields').hidden=!minor;row.querySelectorAll('.guardian-fields input,.guardian-fields select').forEach(x=>x.required=toggle.checked&&minor);});
  section.querySelector('#guardian-permission-row').hidden=!minors;form.elements.guardian_consent.required=toggle.checked&&minors;
 }
 function render(){
  const count=Number(form.elements.guests.value);while(list.children.length>count)list.lastElementChild.remove();
  while(list.children.length<count){const i=list.children.length,row=document.createElement('fieldset');row.className='checkin-guest';row.dataset.index=i;
   row.innerHTML=`<legend>Guest ${i+1}${i===0?' · lead adult':''}</legend><label>Full name<input data-guest-name maxlength="120" autocomplete="off"></label><label>Relationship to lead guest<select data-relationship>${(i===0?['Self']:relationships.filter(r=>r!=='Self')).map(r=>'<option>'+r+'</option>').join('')}</select></label><label class="consent-row"><input type="checkbox" data-minor ${i===0?'disabled':''}><span>Under 18</span></label><div class="guardian-fields" hidden><label>Parent / legal guardian’s full name<input data-guardian-name maxlength="120" autocomplete="off"></label><label>Guardian’s relationship to this minor<select data-guardian-relationship><option value="">Choose</option><option>Father</option><option>Mother</option><option>Legal guardian</option></select></label></div><label>ID image · 2 MB maximum<input data-id type="file" accept="image/jpeg,image/png,image/webp"></label>`;
   if(i===0)row.querySelector('[data-guest-name]').value=form.elements.guest_name.value;list.append(row);
  }
  const leadName=list.querySelector('[data-guest-name]');if(toggle.checked&&leadName&&!leadName.value.trim())leadName.value=form.elements.guest_name.value;
  fields.hidden=!toggle.checked;fields.querySelectorAll('input,select').forEach(x=>x.disabled=!toggle.checked||x.matches('[data-minor]')&&x.closest('.checkin-guest').dataset.index==='0');
  list.querySelectorAll('[data-guest-name],[data-id]').forEach(x=>x.required=toggle.checked);form.elements.id_consent.required=toggle.checked;conditions();
 }
 toggle.addEventListener('change',render);form.elements.guests.addEventListener('change',render);section.addEventListener('change',conditions);
 section.addEventListener('change',e=>{if(e.target.matches('[data-id]'))e.target.setCustomValidity(e.target.files[0]?.size>2*1024*1024?'Please choose an image of 2 MB or smaller.':'');});
 window.BritsmaidGuestRegistration={read(){if(!toggle.checked)return {guests:[],files:[]};const guests=[],files=[];list.querySelectorAll('.checkin-guest').forEach((row,i)=>{guests.push({name:row.querySelector('[data-guest-name]').value.trim(),minor:row.querySelector('[data-minor]').checked,relationship:row.querySelector('[data-relationship]').value,guardian_name:row.querySelector('[data-guardian-name]').value.trim(),guardian_relationship:row.querySelector('[data-guardian-relationship]').value});const file=row.querySelector('[data-id]').files[0];if(file)files.push(['id_'+i,file]);});return {guests,files};}};
 render();
});
