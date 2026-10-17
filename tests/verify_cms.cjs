const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert'),{spawn}=require('child_process');
const root=path.resolve(__dirname,'..'),python='C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const scratch=fs.mkdtempSync(path.join(root,'test-results','browser-cms-'));
const password=require('crypto').randomBytes(20).toString('hex');
const server=spawn(python,['app.py'],{cwd:root,env:{...process.env,PORT:'8012',BRITSMAID_DATA_DIR:scratch,ADMIN_EMAIL:'ui-test@example.invalid',ADMIN_PASSWORD:password},stdio:['ignore','pipe','pipe']});
let serverLog='';server.stderr.on('data',x=>serverLog+=x);
const url='http://127.0.0.1:8012';
(async()=>{
 let browser;
 try{
  for(let i=0;i<80;i++){try{if((await fetch(url+'/health')).ok)break;}catch(e){}if(i===79)throw new Error('Test server unavailable: '+serverLog);await new Promise(r=>setTimeout(r,150));}
  browser=await chromium.launch({headless:true,channel:'msedge'});const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.locator('.pcard').first().waitFor();assert.equal(await page.locator('.pcard').count(),2);
  await page.goto(url+'/stay.html');assert.equal(await page.locator('.pcard[href^="/stays/"]').count(),2);
  await page.selectOption('#f-location','Aluva, Kerala');assert.equal(await page.locator('.pcard:not(.hidden)').count(),1);await page.click('.filter-reset');
  await page.goto(url+'/stays/kumbalangi-villa');assert(await page.locator('h1').innerText().then(x=>x.includes('Divya')));await page.locator('.photo-tile').first().click();assert(await page.locator('.photo-viewer').isVisible());await page.keyboard.press('Escape');
  await page.goto(url+'/admin/login');await page.fill('[name=email]','ui-test@example.invalid');await page.fill('[name=password]',password);await page.getByRole('button',{name:'Sign in to your studio'}).click();await page.locator('#overview-stats .stat').first().waitFor();
  await page.getByRole('button',{name:'Properties 02',exact:true}).click();await page.getByRole('button',{name:'Add a property',exact:false}).filter({visible:true}).click();
  const form=page.locator('#property-form');await form.locator('[name=name]').fill('Local Test Villa');await form.locator('[name=location]').fill('Test locality');await form.locator('[name=summary]').fill('A local test of publishing, never a real listing.');await form.locator('[name=description]').fill('## A test story\nThis property exists only in the isolated test database.');
  await page.locator('#property-photo-select').selectOption({index:1});await page.click('#attach-photo');await form.getByRole('button',{name:'Save property'}).click();await page.locator('#property-dialog').waitFor({state:'hidden'});assert.equal((await fetch(url+'/stays/local-test-villa')).status,404);
  let card=page.locator('.studio-property').filter({hasText:'Local Test Villa'});await card.getByRole('button',{name:'Edit property'}).click();await form.locator('[name=status]').selectOption('published');await form.getByRole('button',{name:'Save property'}).click();await page.locator('#property-dialog').waitFor({state:'hidden'});assert.equal((await fetch(url+'/stays/local-test-villa')).status,200);
  card=page.locator('.studio-property').filter({hasText:'Local Test Villa'});await card.getByRole('button',{name:'Edit property'}).click();await page.locator('#property-photo-upload').setInputFiles(path.join(root,'assets/properties/aluva-villa/img_4009.webp'));await page.waitForFunction(()=>!document.querySelector('#property-photo-upload').disabled);assert.equal(await page.locator('.editor-photo').count(),2);await form.getByRole('button',{name:'Save property'}).click();await page.locator('#property-dialog').waitFor({state:'hidden'});
  await page.locator('[data-tab=reviews]').click();await page.click('#new-review');const review=page.locator('#review-form');await review.locator('[name=name]').fill('Local test guest');await review.locator('[name=quote]').fill('Isolated test review; not published on the real website.');await review.locator('[name=property_id]').selectOption('kumbalangi-villa');await review.locator('[name=status]').selectOption('published');await review.locator('[name=permission]').check();await review.getByRole('button',{name:'Save review'}).click();await page.locator('#review-dialog').waitFor({state:'hidden'});assert((await (await fetch(url)).text()).includes('Isolated test review'));
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   for(const route of ['/','/stay.html','/stays/aluva-villa','/admin']){
    await page.goto(url+route);await page.waitForLoadState('domcontentloaded');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Horizontal overflow ${route} at ${width}`);
    assert(await page.locator('img').first().evaluate(x=>x.complete&&x.naturalWidth>0),'Logo did not load');
   }
  }
  assert.deepEqual(errors,[]);console.log('PASS: real local browser flows — login, filters, gallery, draft/publish, photo upload, review publication, desktop/mobile layout. Isolated test database only.');
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
