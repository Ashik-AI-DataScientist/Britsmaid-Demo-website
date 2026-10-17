// Read-only layout check against the running local preview; no content changes.
const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),assert=require('assert');
(async()=>{const browser=await chromium.launch({headless:true,channel:'msedge'});try{
 const page=await browser.newPage({viewport:{width:1280,height:540}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const credentials=fs.readFileSync('.data/local-login.txt','utf8');await page.goto('http://127.0.0.1:8000/admin/login');await page.fill('[name=email]',credentials.match(/Email: (.+)/)[1].trim());await page.fill('[name=password]',credentials.match(/Password: (.+)/)[1].trim());await page.getByRole('button',{name:'Sign in to your studio'}).click();await page.locator('#overview-stats .stat').first().waitFor();
 for(const viewport of [{width:1280,height:540},{width:960,height:480},{width:1440,height:900},{width:1024,height:360}]){
  await page.setViewportSize(viewport);await page.locator('.studio-sidebar').evaluate(el=>el.scrollTop=0);
  const state=await page.locator('.studio-sidebar').evaluate(el=>({height:el.clientHeight,scroll:el.scrollHeight,overflow:getComputedStyle(el).overflowY}));assert.equal(state.overflow,'auto');assert(state.height<=viewport.height);
  const bodyTop=await page.evaluate(()=>scrollY);await page.mouse.move(100,200);await page.mouse.wheel(0,1200);
  if(state.scroll>state.height)await page.waitForFunction(()=>document.querySelector('.studio-sidebar').scrollTop>0);
  await page.locator('.sidebar-bottom button').focus();
  const bounds=await page.locator('.sidebar-bottom button').boundingBox();assert(bounds.y>=0&&bounds.y+bounds.height<=viewport.height+1,`Sign out clipped at ${JSON.stringify(viewport)}`);assert.equal(await page.evaluate(()=>scrollY),bodyTop,'Sidebar wheel moved the main page');
  await page.locator('[data-tab=settings]').click();assert(await page.locator('#tab-settings').isVisible());
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 }
 await page.setViewportSize({width:960,height:480});await page.locator('.sidebar-bottom button').focus();await page.screenshot({path:'preview-sidebar-short.png'});
 await page.setViewportSize({width:390,height:700});await page.locator('[data-tab=settings]').focus();assert.equal(await page.locator('.studio-sidebar').evaluate(el=>getComputedStyle(el).position),'relative');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 assert.deepEqual(errors,[]);console.log('PASS: independent sidebar wheel scrolling, bottom actions and Settings accessible at four desktop heights (including reduced viewport for zoom), keyboard focus, mobile navigation and no horizontal overflow. No content changed.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
