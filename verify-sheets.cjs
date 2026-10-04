const fs = require('fs'), vm = require('vm'), assert = require('assert');
const rows = [], emails = [];
const sheet = {getLastRow:()=>rows.length,appendRow:r=>rows.push(r),getRange:(r,c,n,w)=>({getValues:()=>[rows[r-1].slice(c-1,c-1+w)],setValue:v=>{rows[r-1][c-1]=v;},createTextFinder:v=>({matchEntireCell:()=>({findNext:()=>rows.slice(1).find(x=>x[1]===v)||null})})})};
const cache = new Map();
const context = vm.createContext({SpreadsheetApp:{openById:()=>({getSheetByName:()=>sheet}),flush:()=>{}},MailApp:{sendEmail:e=>emails.push(e)},LockService:{getScriptLock:()=>({waitLock:()=>{},releaseLock:()=>{}})},CacheService:{getScriptCache:()=>({get:k=>cache.get(k),put:(k,v)=>cache.set(k,v)})}});
vm.runInContext(fs.readFileSync('google-apps-script/Code.gs','utf8'),context);
const payload = {submission_id:'12345678-1234-1234-1234-123456789012',form_type:'management',source_page:'/Britsmaid-Demo-website/partner-with-us.html',consent:{accepted:true,captured_at:new Date().toISOString()},answers:{owner_name:'Test only',phone:'+919747083777',email:'',contact_method:'WhatsApp',contact_time:'Morning',location:'Kochi',property_type:'Villa',bedrooms:'4',furnished:'Fully furnished',current_status:'Vacant',main_goal:'Full property care',consent:'accepted',amenities:['wifi'],proposal_notes:'=IMPORTXML("bad")'}};
assert(context.submitLead(payload).accepted); assert.equal(rows.length,2); assert.equal(emails.length,1);
context.submitLead(payload); assert.equal(rows.length,2); assert.equal(emails.length,1);
assert(rows[1].includes('\'=IMPORTXML("bad")'));
for (const mutate of [p=>p.consent.accepted=false,p=>p.answers.phone='',p=>p.answers.website_url='spam',p=>p.answers.bedrooms='-1',p=>p.source_page='/other/']) {
 const bad=JSON.parse(JSON.stringify(payload));mutate(bad);assert.throws(()=>context.submitLead(bad));
}
const sale = JSON.parse(JSON.stringify(payload));sale.submission_id='12345678-1234-1234-1234-123456789013';sale.form_type='sale';Object.assign(sale.answers,{size:'2000',size_unit:'Square feet',title_status:'Clear title — sole owner',reason:'Moving',timeline:'Flexible',listed_elsewhere:'No',open_to_interim_management:'Yes'});
context.submitLead(sale);assert.equal(rows.length,3);
context.MailApp.sendEmail=()=>{throw new Error('Quota');};sale.submission_id='12345678-1234-1234-1234-123456789014';assert(context.submitLead(sale).accepted);assert.equal(rows[3][7],'Failed — review Sheet');
console.log('Receiver checks passed: both forms, consent/contact validation, duplicate prevention, formula escaping, durable save when alerts fail. No real Sheets writes or emails.');
