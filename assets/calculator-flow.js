'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 const scenarioKey='britsmaid-property-scenario-v2',promptKey='britsmaid-proposal-prompt-v2',lifetime=30*60*1000;
 const proposal=document.querySelector('.lead-form[data-form-type="management"]'),amenities=['pool','gym','garden','parking','ac','wifi'];let promptShown=false;
 const read=key=>{try{return JSON.parse(sessionStorage.getItem(key));}catch(e){return null;}};
 const store=(key,value)=>{try{sessionStorage.setItem(key,JSON.stringify(value));}catch(e){}};
 function clean(value){
  if(!value||typeof value.location!=='string'||!value.location.trim()||value.location.length>2000)return null;
  const bedrooms=Number(value.bedrooms),land=Number(value.land_cents||0);
  if(!Number.isInteger(bedrooms)||bedrooms<1||bedrooms>12||!Number.isFinite(land)||land<0||land>100000)return null;
  const selected=Array.isArray(value.amenities)?value.amenities:[];
  return {location:value.location.trim(),bedrooms,land_cents:land,amenities:[...new Set(selected.filter(x=>amenities.includes(x)))]};
 }
 function prefill(input){
  if(!proposal||!input)return;for(const key of ['location','bedrooms','land_cents'])proposal.elements.namedItem(key).value=input[key];
  proposal.querySelectorAll('[name=amenities]').forEach(el=>el.checked=input.amenities.includes(el.value));proposal.dataset.leadSource='calculator';
  let notice=proposal.querySelector('.proposal-prefill-note');if(!notice){notice=document.createElement('p');notice.className='proposal-prefill-note';notice.setAttribute('role','status');proposal.prepend(notice);}notice.textContent='Your calculator details are filled in below. Check them and add your contact details to request a tailored proposal. Nothing has been submitted yet.';
  window.BritsmaidScenario={input,estimate:window.BritsmaidEarnings.calculate(input)};proposal.dispatchEvent(new Event('proposal:prefilled'));
 }
 const params=new URLSearchParams(location.search),hasExplicit=params.has('bedrooms')||params.has('location')||params.has('land_cents')||params.has('amenities');
 const saved=read(scenarioKey);
 let initial=hasExplicit?clean({bedrooms:params.get('bedrooms'),location:params.get('location')||'',land_cents:params.get('land_cents'),amenities:(params.get('amenities')||'').split(',')}):saved&&Date.now()-saved.saved_at<lifetime?clean(saved.input):null;
 if(proposal&&initial)prefill(initial);
 document.querySelectorAll('.earnings-form').forEach(form=>{
  const result=form.parentElement.querySelector('.estimator-result'),cta=result.querySelector('.calculator-proposal');let scenario=null,dialog=null;
  const error=document.createElement('p');error.className='calculator-error';error.setAttribute('role','alert');form.append(error);
  const hint=document.createElement('p');hint.className='calculator-privacy note';hint.textContent='No name or contact details needed for this estimate. Request a tailored proposal when you are ready.';form.querySelector('[type=submit]').before(hint);
  if(initial){for(const key of ['location','bedrooms','land_cents'])form.elements.namedItem(key).value=initial[key];form.querySelectorAll('[name=amenities]').forEach(el=>el.checked=initial.amenities.includes(el.value));}
  function apply(event){
   if(!scenario)return;store(scenarioKey,{input:scenario,saved_at:Date.now()});
   if(proposal){event?.preventDefault();prefill(scenario);try{const target=new URL(cta.href);history.replaceState(null,'',target.pathname+target.search+'#enquiry');}catch(e){}if(dialog?.open){dialog.dataset.continuing='true';dialog.close();}document.querySelector('#enquiry').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});proposal.elements.owner_name.focus({preventScroll:true});}
  }
  cta.addEventListener('click',apply);
  function prompt(estimate){
   const seen=read(promptKey);if(!('HTMLDialogElement' in window)||promptShown||seen&&Date.now()-seen<lifetime||document.querySelector('dialog[open]'))return;
   if(!dialog){dialog=document.createElement('dialog');dialog.className='proposal-prompt';dialog.setAttribute('aria-labelledby','proposal-prompt-title');dialog.innerHTML='<button type="button" class="proposal-prompt-close" aria-label="Close proposal invitation">×</button><p class="eyebrow">YOUR ESTIMATE IS READY</p><h2 id="proposal-prompt-title">A clearer plan for your home.</h2><p class="proposal-prompt-range"></p><p>This is an illustrative monthly gross revenue range. Let us assess your property and prepare a tailored proposal.</p><p class="note">Your property details carry forward. Your enquiry is only submitted when you complete the proposal form with your contact details and consent.</p><a class="btn-primary" href="">Get my tailored proposal →</a><button type="button" class="proposal-prompt-later">Not now · keep exploring</button>';document.body.append(dialog);dialog.querySelector('a').addEventListener('click',apply);for(const button of dialog.querySelectorAll('button'))button.onclick=()=>dialog.close();dialog.addEventListener('close',()=>{if(!dialog.dataset.continuing)cta.focus({preventScroll:true});delete dialog.dataset.continuing;});}
   dialog.querySelector('.proposal-prompt-range').textContent=estimate;dialog.querySelector('a').href=cta.href;promptShown=true;store(promptKey,Date.now());dialog.showModal();
  }
  form.addEventListener('submit',event=>{
   event.preventDefault();form.elements.location.setCustomValidity(form.elements.location.value.trim()?'':'Please enter your property location.');if(!form.reportValidity())return;
   scenario=clean({location:form.elements.location.value,bedrooms:form.elements.bedrooms.value,land_cents:form.elements.land_cents.value,amenities:new FormData(form).getAll('amenities')});
   if(!scenario){error.textContent='Please check the location, bedrooms and land extent.';return;}
   error.textContent='';const estimate=window.BritsmaidEarnings.calculate(scenario),money=n=>'₹'+n.toLocaleString('en-IN'),range=money(estimate.low)+' – '+money(estimate.high)+' / month';
   result.hidden=false;result.querySelector('.range').textContent=range;result.querySelector('.assumptions').textContent='Illustrative nightly rate: '+money(estimate.nightly)+'; 30-day month at 45–60% occupancy. Before operating costs, fees and taxes. Location is not used in this generic estimate.';
   const query=new URLSearchParams({source:'tailored_proposal',location:scenario.location,bedrooms:scenario.bedrooms,land_cents:scenario.land_cents,amenities:scenario.amenities.join(',')});cta.href='partner-with-us.html?'+query+'#enquiry';
   store(scenarioKey,{input:scenario,saved_at:Date.now()});window.BritsmaidScenario={input:scenario,estimate};prompt(range);
  });
  form.addEventListener('input',()=>{form.elements.location.setCustomValidity('');scenario=null;result.hidden=true;error.textContent='';window.BritsmaidScenario=null;try{sessionStorage.removeItem(scenarioKey);}catch(e){}});
 });
});
