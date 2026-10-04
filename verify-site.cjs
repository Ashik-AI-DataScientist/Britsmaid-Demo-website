const { chromium } = require('C:/Users/HP/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const { pathToFileURL } = require('url');
const path = require('path');
const assert = require('assert');
const earnings = require('./assets/earnings.js');
async function run() {
  const base = earnings.calculate({bedrooms:3,land_cents:0,amenities:[],location:'Kochi'});
  assert.deepEqual(base, earnings.calculate({bedrooms:3,land_cents:0,amenities:[],location:'Thrissur'}));
  assert.equal(base.low,68900); assert.equal(base.high,91800);
  assert(earnings.calculate({bedrooms:3,amenities:['pool']}).high > base.high);
  assert.deepEqual(earnings.calculate({bedrooms:3,land_cents:50}), earnings.calculate({bedrooms:3,land_cents:500}));
  assert.throws(()=>earnings.calculate({bedrooms:0}));
  const browser = await chromium.launch({headless:true,channel:"msedge"});
  const page = await browser.newPage();
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  const open = name => page.goto(pathToFileURL(path.join(process.cwd(),name)).href);
  for(const width of [1440,390]) {
    await page.setViewportSize({width,height:1000});
    for(const name of ['index.html','partner-with-us.html','sell-your-property.html']) {
      await open(name);
      assert(await page.locator('.brand img').evaluate(el=>el.complete&&el.naturalWidth>0));
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow ${name} ${width}`);
      assert(await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(x=>x.id);return ids.length===new Set(ids).size;}),`Duplicate IDs ${name}`);
    }
  }
  await open('index.html');
  await page.locator('.earnings-form input[name=location]').fill('Kochi');
  await page.locator('.earnings-form [value=pool]').check();
  await page.locator('.earnings-form [type=submit]').click();
  assert((await page.locator('.range').innerText()).includes('1,10,200'));
  await page.locator('.calculator-proposal').click();
  assert.equal(await page.locator('.lead-form input[name=location]').inputValue(),'Kochi');
  assert(await page.locator('.lead-form [value=pool]').isChecked());
  const fillRequired = async () => {
    await page.locator('.lead-form input[required]').evaluateAll(els=>els.forEach(el=>{if(el.type==='checkbox') el.checked=true;else if(el.type==='number') el.value='3';else el.value='Test owner';el.dispatchEvent(new Event('input',{bubbles:true}));}));
    await page.locator('.lead-form select[required]').evaluateAll(els=>els.forEach(el=>{el.selectedIndex=1;el.dispatchEvent(new Event('change',{bubbles:true}));}));
  };
  await fillRequired();
  await page.locator('.lead-form [type=submit]').click();
  assert(await page.locator('.lead-form input[name=phone]').evaluate(el=>!el.validity.valid));
  await page.locator('.lead-form select[name=contact_method]').selectOption({label:'Email'});
  await page.locator('.lead-form input[name=email]').fill('owner@example.com');
  await page.locator('.lead-form input[name=consent]').uncheck();
  await page.locator('.lead-form [type=submit]').click();
  assert(!(await page.locator('.download-enquiry').isVisible()));
  await page.locator('.lead-form input[name=consent]').check();
  await page.locator('.lead-form [type=submit]').click();
  assert((await page.locator('.form-status').innerText()).includes('not been sent'));
  await page.evaluate(()=>{window.BritsmaidConfig.leadEndpoint='/api/leads';window.attemptIds=[];window.fetch=async(url,opts)=>{window.attemptIds.push(JSON.parse(opts.body).submission_id);throw new Error('Network unavailable');};});
  await page.locator('.lead-form [type=submit]').click();
  assert((await page.locator('.form-status').innerText()).includes('could not confirm'));
  await page.locator('.lead-form [type=submit]').click();
  assert(await page.evaluate(()=>attemptIds.length===2&&attemptIds[0]===attemptIds[1]));
  assert(await page.locator('.download-enquiry').isVisible());
  await page.evaluate(()=>{window.BritsmaidConfig.leadEndpoint='/api/leads';window.fetch=async(url,opts)=>{window.testPayload=JSON.parse(opts.body);return {ok:true,json:async()=>({accepted:true,submission_id:'test-123'})};};});
  await page.locator('.lead-form [type=submit]').click();
  const payload=await page.evaluate(()=>window.testPayload);
  assert.equal(payload.form_type,'management');assert.equal(payload.answers.email,'owner@example.com');assert(payload.calculator);assert(payload.answers.amenities.includes('pool'));assert(payload.consent.accepted);
  assert((await page.locator('.form-status').innerText()).includes('test-123'));
  await open('sell-your-property.html');await fillRequired();
  await page.locator('.lead-form input[name=phone]').fill('+91 98765 43210');
  await page.locator('.lead-form [type=submit]').click();
  assert((await page.locator('.form-status').innerText()).includes('not been sent'));
  await page.setViewportSize({width:390,height:844});await open('index.html');
  await page.locator('.menu-btn').click();assert.equal(await page.locator('.menu-btn').getAttribute('aria-expanded'),'true');
  await page.keyboard.press('Escape');assert.equal(await page.locator('.menu-btn').getAttribute('aria-expanded'),'false');
  await page.emulateMedia({reducedMotion:'reduce'});await page.mouse.move(200,250);assert.equal(await page.locator('.hero-orbit').evaluate(el=>getComputedStyle(el).transform),'none');
  await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));await page.waitForTimeout(100);await page.mouse.move(1000,300);await page.mouse.move(1100,350);await page.waitForTimeout(200);
  assert.notEqual(await page.locator('.home-hero').evaluate(el=>el.style.getPropertyValue('--cursor-x')),'0px');
  await page.screenshot({path:'homepage-preview.png',fullPage:true});
  assert.deepEqual(errors,[]);await browser.close();console.log('PASS: responsive layout, logo, unique IDs, calculator, proposal prefill, contact/consent validation, preview and mocked backend payload, mobile menu and reduced motion.');
}
run().catch(e=>{console.error(e);process.exit(1)});

