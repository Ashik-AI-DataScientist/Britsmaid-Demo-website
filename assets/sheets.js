/* Apps Script HTML-service bridge: real receipts, without opaque no-cors requests. */
(function () {
  var connection;
  function connect() {
    if (connection) return connection;
    connection = new Promise(function (resolve, reject) {
      var url = new URL(window.BritsmaidConfig.appsScriptUrl);
      if (url.origin !== 'https://script.google.com' || !/^\/macros\/s\/[^/]+\/exec$/.test(url.pathname)) { connection = null; reject(new Error('Invalid deployment')); return; }
      var nonce = crypto.randomUUID(), frame = document.createElement('iframe');
      frame.hidden = true; frame.title = 'Secure enquiry delivery';
      url.searchParams.set('origin', location.origin); url.searchParams.set('nonce', nonce);
      var timer = setTimeout(function () { window.removeEventListener('message', ready); frame.remove(); connection = null; reject(new Error('Receiver unavailable')); }, 25000);
      function ready(event) {
        if (!/^https:\/\/(?:script|[a-z0-9-]+-script)\.googleusercontent\.com$/.test(event.origin) || !event.data || event.data.kind !== 'britsmaid:ready' || event.data.nonce !== nonce) return;
        clearTimeout(timer); window.removeEventListener('message', ready);
        resolve({source:event.source, origin:event.origin, nonce:nonce});
      }
      window.addEventListener('message', ready); frame.src = url.href; document.body.appendChild(frame);
    });
    return connection;
  }
  window.BritsmaidSheets = {submit: async function (payload) {
    var bridge = await connect();
    return new Promise(function (resolve, reject) {
      var request = crypto.randomUUID();
      var timer = setTimeout(function () { window.removeEventListener('message', receive); reject(new Error('Delivery not confirmed')); }, 45000);
      function receive(event) {
        var data = event.data;
        if (event.source !== bridge.source || event.origin !== bridge.origin || !data || data.nonce !== bridge.nonce || data.request !== request) return;
        clearTimeout(timer); window.removeEventListener('message', receive);
        if (data.kind === 'britsmaid:receipt' && data.receipt && data.receipt.accepted && data.receipt.submission_id === payload.submission_id) resolve(data.receipt);
        else reject(new Error('Receiver rejected enquiry'));
      }
      window.addEventListener('message', receive);
      bridge.source.postMessage({kind:'britsmaid:submit',nonce:bridge.nonce,request:request,payload:payload}, bridge.origin);
    });
  }};
}());
