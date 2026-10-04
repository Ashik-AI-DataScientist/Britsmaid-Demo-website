const SETTINGS = {
  sheetId: '15PSGnAJaCbfbyKWLcd6m_wSe9X-q39_Am5n7bkn3fMw',
  sheetName: 'Website enquiries',
  alertEmail: 'ashikmasharaf97@gmail.com',
  origins: ['https://ashik-ai-datascientist.github.io'],
  pathPrefix: '/Britsmaid-Demo-website/'
};
const FIELDS = ['owner_name','phone','email','contact_method','contact_time','location','property_type','bedrooms','furnished','built_up_sqft','land_cents','current_status','main_goal','amenities','amenities_notes','listing_url','ready_date','size','size_unit','expected_price','title_status','reason','timeline','listed_elsewhere','open_to_interim_management','proposal_notes'];
const HEADERS = ['Received at','Reference','Form type','Source page','Stage','Team notes','Follow up','Alert status'].concat(FIELDS, ['Consent accepted','Consent captured at','Full submission JSON']);

function doGet(e) {
  const origin = String(e.parameter.origin || '');
  const nonce = String(e.parameter.nonce || '');
  if (!SETTINGS.origins.includes(origin) || !/^[a-z0-9-]{36}$/i.test(nonce)) return HtmlService.createHtmlOutput('Britsmaid enquiry receiver.');
  const template = HtmlService.createTemplateFromFile('Bridge');
  template.parentOrigin = origin; template.nonce = nonce;
  return template.evaluate().setTitle('Britsmaid enquiry receiver').setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// Run once in the editor to initialise the private sheet and authorise Sheets/email access.
function setup() { const sheet = sheet_(); sheet.setFrozenRows(1); sheet.getRange(1,1,1,HEADERS.length).setFontWeight('bold'); MailApp.getRemainingDailyQuota(); }
function sheet_() {
  const book = SpreadsheetApp.openById(SETTINGS.sheetId);
  const sheet = book.getSheetByName(SETTINGS.sheetName) || book.insertSheet(SETTINGS.sheetName);
  if (!sheet.getLastRow()) sheet.appendRow(HEADERS);
  if (JSON.stringify(sheet.getRange(1,1,1,HEADERS.length).getValues()[0]) !== JSON.stringify(HEADERS)) throw new Error('Unexpected sheet columns');
  return sheet;
}
function safe_(value) {
  const text = Array.isArray(value) ? value.join(', ') : String(value == null ? '' : value);
  return /^[\s]*[=+@-]/.test(text) ? "'" + text : text;
}
function validate_(payload) {
  if (!payload || JSON.stringify(payload).length > 16000 || !/^[a-z0-9-]{36}$/i.test(payload.submission_id || '') || !['management','sale'].includes(payload.form_type)) throw new Error('Invalid enquiry');
  if (!String(payload.source_page || '').startsWith(SETTINGS.pathPrefix) || !payload.consent || payload.consent.accepted !== true || !Number.isFinite(Date.parse(payload.consent.captured_at))) throw new Error('Invalid consent or source');
  const a = payload.answers;
  if (!a || a.website_url || a.consent !== 'accepted') throw new Error('Invalid form');
  Object.keys(a).forEach(function (key) { if (!FIELDS.includes(key) && !['consent','website_url'].includes(key)) throw new Error('Unknown field'); if (typeof a[key] !== 'string' && !(key === 'amenities' && Array.isArray(a[key]))) throw new Error('Invalid field'); if (JSON.stringify(a[key]).length > 2500) throw new Error('Field too long'); });
  const required = ['owner_name','contact_method','contact_time','location','property_type'].concat(payload.form_type === 'management' ? ['bedrooms','furnished','current_status','main_goal'] : ['size','size_unit','title_status','reason','timeline','listed_elsewhere','open_to_interim_management']);
  required.forEach(function (key) { if (!String(a[key] || '').trim()) throw new Error('Missing field'); });
  const phone = String(a.phone || '').trim(), email = String(a.email || '').trim();
  if ((!phone && !email) || (phone && (!/^\+?[\d\s().-]+$/.test(phone) || phone.replace(/\D/g,'').length < 7 || phone.replace(/\D/g,'').length > 15)) || (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) throw new Error('Invalid contact');
  if (!['Email','WhatsApp','Phone call'].includes(a.contact_method) || (a.contact_method === 'Email' ? !email : !phone)) throw new Error('Contact method mismatch');
  ['bedrooms','built_up_sqft','land_cents','size','expected_price'].forEach(function (key) { if (a[key] && (!Number.isFinite(Number(a[key])) || Number(a[key]) < 0 || Number(a[key]) > 1e12)) throw new Error('Invalid number'); });
  if (payload.form_type === 'management' && (!Number.isInteger(Number(a.bedrooms)) || Number(a.bedrooms) < 1 || Number(a.bedrooms) > 30)) throw new Error('Invalid bedrooms');
  if (payload.form_type === 'sale' && Number(a.size) <= 0) throw new Error('Invalid size');
  if (a.amenities && (!Array.isArray(a.amenities) || a.amenities.length > 6 || a.amenities.some(function (x) {return !['pool','gym','garden','parking','ac','wifi'].includes(x);}))) throw new Error('Invalid amenities');
  return a;
}
function submitLead(payload) {
  const answers = validate_(payload);
  const lock = LockService.getScriptLock(); lock.waitLock(20000);
  try {
    const sheet = sheet_();
    if (sheet.getLastRow() > 1 && sheet.getRange(2,2,sheet.getLastRow()-1,1).createTextFinder(payload.submission_id).matchEntireCell(true).findNext()) return {accepted:true,submission_id:payload.submission_id};
    // Small-demo abuse ceiling. This public receiver is not a full anti-bot service.
    const cache = CacheService.getScriptCache(), key = 'hour:' + Math.floor(Date.now()/3600000), count = Number(cache.get(key) || 0);
    if (count >= 100) throw new Error('Please contact us directly');
    cache.put(key,String(count+1),3600);
    const row = [new Date().toISOString(),payload.submission_id,payload.form_type,payload.source_page,'New','','','Pending'].concat(FIELDS.map(function (key) {return safe_(answers[key]);}),['Yes',payload.consent.captured_at,safe_(JSON.stringify(payload))]);
    sheet.appendRow(row); SpreadsheetApp.flush();
    const rowNumber = sheet.getLastRow();
    try {
      MailApp.sendEmail({to:SETTINGS.alertEmail,subject:'New Britsmaid ' + payload.form_type + ' enquiry',body:'A new website enquiry was saved. Reference: ' + payload.submission_id + '\nReview it in your private Sheet: https://docs.google.com/spreadsheets/d/' + SETTINGS.sheetId + '/edit'});
      sheet.getRange(rowNumber,8).setValue('Sent');
    } catch (error) { sheet.getRange(rowNumber,8).setValue('Failed — review Sheet'); }
    return {accepted:true,submission_id:payload.submission_id};
  } finally { lock.releaseLock(); }
}
