'use strict';
window.BritsmaidLeads={async submit(draft){try{
 const timeout=ms=>typeof AbortSignal.timeout==='function'?AbortSignal.timeout(ms):undefined;
 const auth=await fetch('/api/public-session',{cache:'no-store',signal:timeout(10000)});if(!auth.ok)throw Error('Please refresh and try again.');const {csrf}=await auth.json();
 const payload={...draft,request_id:draft.submission_id,consent:draft.consent?.accepted===true,website_url:draft.answers.website_url||''};
 const response=await fetch('/api/leads',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(payload),signal:timeout(20000)});let data;try{data=await response.json();}catch(e){throw Error('Delivery could not be confirmed. Please try again.');}if(!response.ok)throw Error(data.error||'Delivery could not be confirmed.');if(!data.accepted||!data.submission_id)throw Error('The server did not return a receipt. Retry to confirm delivery.');return data;
}catch(error){if(['AbortError','TimeoutError'].includes(error.name))throw Error('Connection timed out. Your answers are still here; retry to confirm delivery.');if(error instanceof TypeError)throw Error('Connection interrupted. Check your internet connection and retry.');throw error;}
}};
