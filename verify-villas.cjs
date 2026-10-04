const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const {pathToFileURL}=require('url');const path=require('path');const assert=require('assert');const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const open=name=>page.goto(pathToFileURL(path.join(process.cwd(),name)).href);
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});
  for(const name of ['index.html','stay.html','aluva-villa.html','kumbalangi-villa.html','property-detail.html']){
   await open(name);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow: ${name} ${width}`);
   const paths=await page.locator('img').evaluateAll(imgs=>imgs.filter(i=>i.getAttribute("src")).map(i=>new URL(i.src).pathname));
   paths.forEach(p=>assert(fs.existsSync(decodeURIComponent(p).replace(/^\/(\w:)/,'$1')),p));
   assert((await page.locator('body').innerText()).includes('contact@britsmaid.in'));
   assert.equal(await page.locator('a[href="tel:+910000000000"]').count(),0);
  }
 }
 await open('stay.html');assert.equal(await page.locator('.pcard').count(),2);
 await page.selectOption('#f-location','kumbalangi');assert.equal(await page.locator('.pcard:visible').count(),1);assert((await page.locator('.pcard:visible').innerText()).includes('6 beds'));
 await page.locator('.filter-reset').click();assert.equal(await page.locator('.pcard:visible').count(),2);
 for(const name of ['aluva-villa.html','kumbalangi-villa.html']){
  await open(name);await page.locator('.photo-tile').first().click();assert(await page.locator('.photo-viewer').isVisible());
  assert((await page.locator('.photo-counter').innerText()).startsWith('1 /'));
  await page.keyboard.press('ArrowRight');assert((await page.locator('.photo-counter').innerText()).startsWith('2 /'));
  await page.keyboard.press('Escape');assert(!(await page.locator('.photo-viewer').isVisible()));
  await page.evaluate(()=>{document.addEventListener('click',e=>{const a=e.target.closest('a');if(a&&/^(https:\/\/wa.me|mailto:)/.test(a.href)){e.preventDefault();window.testLink=a.href;}},true);document.querySelector('.booking-enquiry').addEventListener('booking:prepared',e=>window.testMessage=e.detail);});
  await page.fill('#check-in','2099-05-20');await page.fill('#check-out','2099-05-19');await page.fill('#booking-notes','Airport pickup? & late arrival');
  await page.locator('.booking-enquiry [name=consent]').check();await page.locator('.booking-enquiry button[value=whatsapp]').click();
  assert(await page.locator('#check-out').evaluate(el=>!el.validity.valid));assert.equal(await page.evaluate(()=>window.testMessage),undefined);
  await page.fill('#check-out','2099-05-25');await page.fill('#guests','8');await page.locator('.booking-enquiry button[value=whatsapp]').click();
  let data=await page.evaluate(()=>window.testMessage);assert(data.href.startsWith('https://wa.me/919747083777?'));assert(data.message.includes('Guests: 8'));assert(data.message.includes('20 May 2099'));assert(data.message.includes('Airport pickup? & late arrival'));assert(data.message.includes(name==='aluva-villa.html'?'Aluva':'Kumbalangi'));
  await page.locator('.booking-enquiry button[value=email]').click();data=await page.evaluate(()=>window.testMessage);assert(data.href.startsWith('mailto:contact@britsmaid.in?'));assert.equal(data.channel,'email');assert(decodeURIComponent(data.href).includes('25 May 2099'));
 }
 await page.setViewportSize({width:1440,height:1000});await open('aluva-villa.html');await page.screenshot({path:'aluva-villa-preview.png',fullPage:true});
 assert.deepEqual(errors,[]);await browser.close();console.log('PASS: two real listings, desktop/mobile layouts, all photo paths, location filters, photo viewer navigation, invalid dates, and complete WhatsApp/email drafts for both villas. No messages sent.');
})().catch(e=>{console.error(e);process.exit(1);});

