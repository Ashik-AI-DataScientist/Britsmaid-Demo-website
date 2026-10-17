'use strict';
window.BritsmaidLeads={async submit(draft){
 const auth=await fetch('/api/public-session',{cache:'no-store'});if(!auth.ok)throw Error('Please refresh and try again.');const {csrf}=await auth.json();
 const payload={...draft,request_id:draft.submission_id,consent:true,website_url:draft.answers.website_url||''};
 const response=await fetch('/api/leads',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(payload)});let data;try{data=await response.json();}catch(e){throw Error('Delivery could not be confirmed. Please try again.');}if(!response.ok)throw Error(data.error||'Delivery could not be confirmed.');return data;
}};
