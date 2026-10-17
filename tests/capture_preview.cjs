const {chromium}=require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  await page.goto('http://127.0.0.1:8000/');await page.waitForLoadState('networkidle');await page.screenshot({path:'preview-homepage.png'});
  await page.goto('http://127.0.0.1:8000/stays/aluva-villa');await page.waitForLoadState('networkidle');await page.screenshot({path:'preview-villa.png'});
  const credentials=fs.readFileSync(path.join('.data','local-login.txt'),'utf8');
  await page.goto('http://127.0.0.1:8000/admin/login');await page.fill('[name=email]',credentials.match(/Email: (.+)/)[1].trim());await page.fill('[name=password]',credentials.match(/Password: (.+)/)[1].trim());await page.getByRole('button',{name:'Sign in to your studio'}).click();await page.locator('#overview-stats .stat').first().waitFor();await page.waitForLoadState('networkidle');await page.screenshot({path:'preview-admin.png'});
  await page.locator('[data-tab=properties]').click();await page.screenshot({path:'preview-admin-properties.png'});
  await page.locator('[data-tab=bookings]').click();await page.waitForTimeout(300);await page.screenshot({path:'preview-bookings.png'});
  await page.locator('[data-tab=calendars]').click();await page.waitForTimeout(300);await page.screenshot({path:'preview-calendars.png'});
  await page.locator('[data-tab=crm]').click();await page.waitForTimeout(300);await page.screenshot({path:'preview-crm.png'});
  await page.goto('http://127.0.0.1:8000/feedback');await page.waitForLoadState('networkidle');await page.screenshot({path:'preview-feedback.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});await page.goto('http://127.0.0.1:8000/');await page.waitForLoadState('networkidle');await page.screenshot({path:'preview-mobile.png'});
  await page.goto('http://127.0.0.1:8000/admin');await page.locator('#overview-stats .stat').first().waitFor();await page.screenshot({path:'preview-admin-mobile.png'});
  console.log('Saved desktop and mobile previews. No content was changed.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
