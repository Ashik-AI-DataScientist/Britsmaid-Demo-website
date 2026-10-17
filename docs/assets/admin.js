'use strict';
(function () {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => Array.from(root.querySelectorAll(s));
  const token = $('meta[name="csrf-token"]').content;
  let content, currentPhotos=[], editorId=null, dirty=false;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const badge = status => `<span class="badge ${esc(status)}">${esc(status)}</span>`;
  const status = (message,error=false) => {$('#app-status').textContent=message;$('#app-status').classList.toggle('error',error);};
  async function api(path, data, method='POST') {
    const response = await fetch(path,{method,headers:{'X-CSRF-Token':token,...(data instanceof FormData?{}:{'Content-Type':'application/json'})},body:data instanceof FormData?data:JSON.stringify(data)});
    if(response.status===401){location.href='/admin/login';throw new Error('Sign in again.');}
    let result;try{result=await response.json();}catch(e){throw new Error('The server did not confirm the change. Please try again.');}
    if(!response.ok)throw new Error(result.error||'The change could not be saved.');
    return result;
  }
  function tab(name){
    $$('.studio-tab').forEach(x=>x.hidden=x.id!=='tab-'+name);
    $$('.nav-item').forEach(x=>{x.classList.toggle('active',x.dataset.tab===name);x.setAttribute('aria-current',x.dataset.tab===name?'page':'false');});
    history.replaceState(null,'','#'+name);status('');
  }
  function mediaItems(){
    const items=new Map();
    content.properties.forEach(p=>p.photos.forEach(photo=>items.set(photo.url,photo)));
    content.media.forEach(photo=>items.set(photo.url,photo));
    return Array.from(items.values());
  }
  function renderProperties(){
    const search=$('#property-search').value.toLowerCase(), filter=$('#property-status').value;
    const items=content.properties.filter(p=>(!filter||p.status===filter)&&`${p.name} ${p.location}`.toLowerCase().includes(search));
    $('#property-list').innerHTML=items.map(p=>`<article class="studio-property">${p.photos[0]?`<img src="${esc(p.photos[0].url)}" alt="${esc(p.photos[0].alt)}" loading="lazy">`:''}<div class="card-body">${badge(p.status)}<h2>${esc(p.name)}</h2><p>${esc(p.location)}<br>${p.bedrooms} bedrooms · ${p.guests} guests · ${p.photos.length} photographs</p><div class="card-actions"><button class="secondary" data-edit-property="${esc(p.id)}">Edit property</button>${p.status==='published'?`<a href="/stays/${esc(p.slug)}" target="_blank" rel="noopener">View stay ↗</a>`:'<span class="muted">Not on the website</span>'}</div></div></article>`).join('')||'<div class="empty"><h2>Room for something new.</h2><p>No properties match this selection.</p></div>';
  }
  function render(){
    const published=content.properties.filter(p=>p.status==='published').length;
    $('#overview-stats').innerHTML=[[published,'Published homes'],[content.properties.length-published,'Drafts & archived homes'],[content.reviews.filter(r=>r.status==='published').length,'Published guest reviews']].map(([n,label])=>`<div class="stat"><strong>${n.toString().padStart(2,'0')}</strong><span>${label}</span></div>`).join('');
    $('#overview-properties').innerHTML=content.properties.slice(0,3).map(p=>`<div class="mini-property">${p.photos[0]?`<img src="${esc(p.photos[0].url)}" alt="${esc(p.photos[0].alt)}">`:''}<div><strong>${esc(p.name)}</strong><small>${esc(p.location)}</small></div>${badge(p.status)}</div>`).join('')||'<p class="muted">Add your first home to begin.</p>';
    $('#activity-list').innerHTML=content.activity.map(a=>`<div class="activity-row"><span>${esc(a.action)}</span><time>${esc(new Date(a.created_at).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short'}))}</time></div>`).join('')||'<p class="muted">Your publishing activity will appear here.</p>';
    renderProperties();
    $('#review-list').innerHTML=content.reviews.map(r=>`<article class="panel"><div class="review-meta">${badge(r.status==='draft'&&r.submission_source==='website'?'awaiting review':r.status)}<button class="secondary" data-edit-review="${esc(r.id)}">Edit review</button></div><blockquote>“${esc(r.quote)}”</blockquote><strong>${esc(r.name)}</strong>${r.contact_email?'<p class="muted">Private contact: '+esc(r.contact_email)+'</p>':''}${r.status==='published'?'<button class="text-button" data-unpublish-review="'+esc(r.id)+'">Unpublish review</button>':''}<p class="muted">${esc(content.properties.find(p=>p.id===r.property_id)?.name||'Britsmaid')} · ${esc(r.source||'Direct guest feedback')}${r.stay_month?' · '+esc(r.stay_month):''}</p></article>`).join('')||'<div class="empty"><h2>Let your guests tell the story.</h2><p>No reviews yet. Add genuine feedback when you have permission to publish it.<br>There are no sample or invented reviews on your website.</p></div>';
    $('#media-list').innerHTML=mediaItems().map(photo=>`<figure class="media-item"><img src="${esc(photo.url)}" alt="${esc(photo.alt)}" loading="lazy"><figcaption>${esc(photo.alt)}<a href="${esc(photo.url)}" target="_blank" rel="noopener">View photograph ↗</a></figcaption></figure>`).join('')||'<div class="empty">Your photographs will appear here.</div>';
    const settings=$('#settings-form');
    $('#hero-image').innerHTML=[{url:'/assets/villa-exterior.jpg',alt:'Original premium villa homepage photograph'},...mediaItems()].map(x=>`<option value="${esc(x.url)}">${esc(x.alt)}</option>`).join('');
    for(const [k,v] of Object.entries(content.settings)){if(settings.elements[k])settings.elements[k].value=v;}
    previewSEO();
  }
  async function reload(){
    const response=await fetch('/admin/api/content',{cache:'no-store'});if(response.status===401){location.href='/admin/login';return;}
    if(!response.ok)throw new Error('Unable to load your studio. Refresh and try again.');content=await response.json();render();
  }
  function libraryOptions(){
    $('#property-photo-select').innerHTML='<option value="">Choose a photograph</option>'+mediaItems().map(p=>`<option value="${esc(p.url)}">${esc(p.alt)}</option>`).join('');
  }
  function renderPhotos(){
    $('#property-photos').innerHTML=currentPhotos.map((photo,i)=>`<div class="editor-photo"><img src="${esc(photo.url)}" alt="${esc(photo.alt)}"><label>${i===0?'COVER PHOTOGRAPH':'Photo '+(i+1)}<input value="${esc(photo.alt)}" data-photo-alt="${i}" maxlength="220" required aria-label="Description for photo ${i+1}"></label><div class="photo-buttons"><button type="button" data-photo-up="${i}" ${i===0?'disabled':''} aria-label="Move photo ${i+1} earlier">↑</button><button type="button" data-photo-down="${i}" ${i===currentPhotos.length-1?'disabled':''} aria-label="Move photo ${i+1} later">↓</button><button type="button" data-photo-remove="${i}" aria-label="Remove photo ${i+1} from property">×</button></div></div>`).join('');
  }
  function editProperty(id){
    const p=content.properties.find(p=>p.id===id)||{id:'',version:'',name:'',slug:'',location:'',summary:'',description:'',category:'Entire private villa',bedrooms:1,beds:1,bathrooms:1,guests:2,nightly_rate:'',amenities:[],status:'draft',featured:false,photos:[],seo_title:'',seo_description:''};
    const form=$('#property-form');form.reset();
    for(const [k,v] of Object.entries(p)){if(form.elements[k]){if(form.elements[k].type==='checkbox')form.elements[k].checked=!!v;else form.elements[k].value=k==='amenities'?v.join('\n'):v??'';}}
    editorId=p.id;currentPhotos=p.photos.map(x=>({...x}));dirty=false;
    form.elements.slug.readOnly=!!p.id;$('#property-dialog-title').textContent=p.id?p.name:'A new chapter.';
    $('.editor-error',form).textContent='';libraryOptions();renderPhotos();$('#property-dialog').showModal();
  }
  function editReview(id){
    const form=$('#review-form');form.reset();
    $('#review-property').innerHTML='<option value="">Britsmaid · general feedback</option>'+content.properties.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');
    const r=content.reviews.find(r=>r.id===id)||{id:'',name:'',quote:'',property_id:'',source:'',source_url:'',stay_month:'',status:'draft',permission:false};
    for(const [k,v] of Object.entries(r)){if(form.elements[k]){if(form.elements[k].type==='checkbox')form.elements[k].checked=!!v;else form.elements[k].value=v??'';}}
    $('.editor-error',form).textContent='';dirty=false;$('#review-dialog').showModal();
  }
  function closeDialog(dialog){if(dirty&&!confirm('Close without saving these changes?'))return;dialog.close();dirty=false;}
  $$('.nav-item').forEach(button=>button.addEventListener('click',()=>tab(button.dataset.tab)));
  $$('[data-action="new-property"]').forEach(button=>button.addEventListener('click',()=>editProperty()));
  $('[data-action="show-properties"]').addEventListener('click',()=>tab('properties'));
  $('#new-review').addEventListener('click',()=>editReview());
  $('#property-list').addEventListener('click',e=>{const button=e.target.closest('[data-edit-property]');if(button)editProperty(button.dataset.editProperty);});
  $('#review-list').addEventListener('click',async e=>{const button=e.target.closest('[data-edit-review]');if(button)editReview(button.dataset.editReview);const unpublish=e.target.closest('[data-unpublish-review]');if(unpublish){unpublish.disabled=true;try{await api('/admin/api/reviews/'+encodeURIComponent(unpublish.dataset.unpublishReview)+'/unpublish',{});await reload();status('Review unpublished. It remains available in your studio.');}catch(error){status(error.message,true);unpublish.disabled=false;}}});
  $$('.close-dialog').forEach(button=>button.addEventListener('click',()=>closeDialog(button.closest('dialog'))));
  $$('dialog').forEach(dialog=>{dialog.addEventListener('cancel',e=>{e.preventDefault();closeDialog(dialog);});dialog.addEventListener('input',()=>dirty=true);});
  $('#property-search').addEventListener('input',renderProperties);$('#property-status').addEventListener('change',renderProperties);
  $('#property-form').elements.name.addEventListener('input',e=>{if(!editorId)$('#property-form').elements.slug.value=e.target.value.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');});
  $('#property-photos').addEventListener('input',e=>{if(e.target.dataset.photoAlt!==undefined){currentPhotos[Number(e.target.dataset.photoAlt)].alt=e.target.value;dirty=true;}});
  $('#property-photos').addEventListener('click',e=>{
    const b=e.target.closest('button');if(!b)return;let i;
    if(b.dataset.photoRemove!==undefined){currentPhotos.splice(Number(b.dataset.photoRemove),1);}
    else if(b.dataset.photoUp!==undefined){i=Number(b.dataset.photoUp);[currentPhotos[i-1],currentPhotos[i]]=[currentPhotos[i],currentPhotos[i-1]];}
    else if(b.dataset.photoDown!==undefined){i=Number(b.dataset.photoDown);[currentPhotos[i+1],currentPhotos[i]]=[currentPhotos[i],currentPhotos[i+1]];}
    dirty=true;renderPhotos();
  });
  $('#attach-photo').addEventListener('click',()=>{const photo=mediaItems().find(x=>x.url===$('#property-photo-select').value);if(photo&&!currentPhotos.some(x=>x.url===photo.url)){currentPhotos.push({...photo});dirty=true;renderPhotos();}});
  async function uploadFiles(files,alt,onPhoto){
    for(const [i,file] of Array.from(files).entries()){
      if(file.size>12*1024*1024)throw new Error(file.name+' is larger than 12 MB.');
      const data=new FormData();data.set('photo',file);data.set('alt',`${alt}${files.length>1?' — photo '+(i+1):''}`.slice(0,220));
      const photo=await api('/admin/api/media',data);content.media.unshift(photo);if(onPhoto)onPhoto(photo);
    }
  }
  $('#property-photo-upload').addEventListener('change',async e=>{
    const input=e.target;input.disabled=true;$('#property-form [type="submit"]').disabled=true;$('.editor-error',$('#property-form')).textContent='Uploading photographs…';
    try{await uploadFiles(input.files,$('#property-form').elements.name.value||'Property photograph',photo=>{currentPhotos.push(photo);dirty=true;renderPhotos();});libraryOptions();$('.editor-error',$('#property-form')).textContent='';}
    catch(error){$('.editor-error',$('#property-form')).textContent=error.message;}finally{input.disabled=false;input.value='';$('#property-form [type="submit"]').disabled=false;}
  });
  async function saveForm(event,path,build){
    event.preventDefault();const form=event.target,button=$('[type="submit"]',form);button.disabled=true;
    const errorEl=$('.editor-error',form);if(errorEl)errorEl.textContent='';
    try{await api(path,build(form));dirty=false;form.closest('dialog')?.close();await reload();status('Saved. Published changes are now reflected on the website.');}
    catch(error){if(errorEl)errorEl.textContent=error.message;else status(error.message,true);}finally{button.disabled=false;}
  }
  $('#property-form').addEventListener('submit',e=>saveForm(e,'/admin/api/properties',form=>{const d=Object.fromEntries(new FormData(form));d.version=Number(d.version);d.featured=form.elements.featured.checked;d.amenities=d.amenities.split('\n').map(x=>x.trim()).filter(Boolean);d.photos=currentPhotos;return d;}));
  $('#review-form').addEventListener('submit',e=>saveForm(e,'/admin/api/reviews',form=>({...Object.fromEntries(new FormData(form)),permission:form.elements.permission.checked})));
  $('#settings-form').addEventListener('submit',e=>saveForm(e,'/admin/api/settings',form=>Object.fromEntries(new FormData(form))));
  function previewSEO(){const form=$('#settings-form');$('#seo-preview').innerHTML=`<small>${esc(form.elements.site_url.value||'Your final website address')}</small><strong>${esc(form.elements.home_seo_title.value)}</strong><p>${esc(form.elements.home_seo_description.value)}</p>`;}
  $('#settings-form').addEventListener('input',previewSEO);
  $('#media-upload').addEventListener('submit',async e=>{e.preventDefault();const form=e.target,button=$('button',form);button.disabled=true;status('Uploading and optimising photographs…');try{await uploadFiles(form.elements.photos.files,form.elements.alt.value);await reload();form.reset();status('Photographs added to your library. Attach them to a property when ready.');}catch(error){status(error.message,true);}finally{button.disabled=false;}});
  $('#password-form').addEventListener('submit',async e=>{e.preventDefault();const form=e.target,button=$('button',form);button.disabled=true;try{await api('/admin/api/password',Object.fromEntries(new FormData(form)));location.href='/admin/login';}catch(error){status(error.message,true);button.disabled=false;}});
  window.addEventListener('beforeunload',event=>{if(dirty&&$$('dialog[open]').length){event.preventDefault();event.returnValue='';}});
  window.BritsmaidStudio={api,reload,status};
  reload().then(()=>{const requested=location.hash.slice(1);if(['overview','properties','reviews','bookings','calendars','media','crm','settings'].includes(requested))tab(requested);}).catch(error=>status(error.message,true));
}());
