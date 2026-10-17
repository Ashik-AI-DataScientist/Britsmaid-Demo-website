'use strict';
(function(){
 const base=new URL('../',document.currentScript.src).pathname;
 const key='britsmaid-cookie-choice-v1',life=180*86400000;let choice;
 try{choice=JSON.parse(localStorage.getItem(key));}catch(e){}
 const banner=document.createElement('section');banner.className='cookie-banner';banner.setAttribute('aria-label','Cookie preferences');banner.innerHTML='<div><strong>A little privacy, by default.</strong><p>We use essential cookies for secure forms and admin sign-in. No analytics or advertising cookies are currently installed. <a href="/cookie-policy.html">Cookie notice</a></p></div><div class="cookie-actions"><button type="button" data-cookie-essential>Use essential only</button><button type="button" data-cookie-manage>Cookie settings</button></div>';
 banner.querySelector('a').href=base+'cookie-policy.html';
 banner.hidden=!!(choice?.version===1&&choice.essential===true&&Date.now()-choice.saved_at<life);document.body.append(banner);
 const dialog=document.createElement('dialog');dialog.className='cookie-dialog';dialog.innerHTML='<form method="dialog"><h2>Your cookie preferences.</h2><p>Essential cookies protect form submissions and keep admins signed in. They are always enabled when needed.</p><label><input type="checkbox" checked disabled> Essential cookies · required</label><label><input type="checkbox" disabled> Analytics · not installed</label><label><input type="checkbox" disabled> Advertising · not installed</label><p>We will ask again if optional tracking is introduced. Your choice is saved on this browser for 180 days.</p><button value="save">Save preferences</button><button value="cancel">Close</button></form>';document.body.append(dialog);
 function save(){choice={version:1,essential:true,analytics:false,advertising:false,saved_at:Date.now()};try{localStorage.setItem(key,JSON.stringify(choice));}catch(e){}banner.hidden=true;}
 banner.querySelector('[data-cookie-essential]').onclick=save;banner.querySelector('[data-cookie-manage]').onclick=()=>dialog.showModal();dialog.addEventListener('close',()=>{if(dialog.returnValue==='save')save();});
 const footer=document.querySelector('footer');if(footer){const button=document.createElement('button');button.type='button';button.className='cookie-reopen';button.textContent='Cookie preferences';button.onclick=()=>dialog.showModal();footer.append(button);}
})();
