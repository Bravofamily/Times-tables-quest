/* NumiRealm v33 offline mode (CR33-4). Promise: while offline mode is on, this device makes NO network
   request to any other host (no Supabase, no Game Night server, no fonts/CDNs) and no version check.
   Only the game's own files from this same site load (served from the service-worker cache after the first visit).
   Turn on with ?localonly=1, off with ?localonly=0. Stored per device (localStorage). Loaded first in <head>. */
(function(){var on=false;try{var s=location.search;if(/[?&]localonly=1(&|$)/.test(s))localStorage.setItem('nr-localonly','1');if(/[?&]localonly=0(&|$)/.test(s))localStorage.removeItem('nr-localonly');on=localStorage.getItem('nr-localonly')==='1';}catch(e){}
 window.NR_LOCALONLY=on;window.NR_OFFLINE_BLOCKED=[];if(!on)return;
 var O=location.origin;function bad(u){try{var x=new URL(String(u&&u.url||u),location.href);if(x.protocol==='data:'||x.protocol==='blob:')return false;if(x.origin!==O)return true;return /\/version\.json$/.test(x.pathname);}catch(e){return true;}}
 function note(u){try{window.NR_OFFLINE_BLOCKED.push(String(u&&u.url||u));}catch(e){}}
 var f=window.fetch;if(f)window.fetch=function(u,o){if(bad(u)){note(u);return Promise.reject(new TypeError('offline_mode'));}return f.apply(this,arguments);};
 var X=window.XMLHttpRequest;if(X){var op=X.prototype.open;X.prototype.open=function(m,u){if(bad(u)){note(u);throw new Error('offline_mode');}return op.apply(this,arguments);};}
 if(navigator.sendBeacon){var sb=navigator.sendBeacon.bind(navigator);navigator.sendBeacon=function(u,d){if(bad(u)){note(u);return false;}return sb(u,d);};}
 var W=window.WebSocket;if(W){window.WebSocket=function(u,p){if(bad(u)){note(u);throw new Error('offline_mode');}return new W(u,p);};}
 var E=window.EventSource;if(E){window.EventSource=function(u,o){if(bad(u)){note(u);throw new Error('offline_mode');}return new E(u,o);};}
 document.addEventListener('DOMContentLoaded',function(){var b=document.createElement('div');b.id='nrOfflineBadge';b.setAttribute('role','status');b.textContent='📴 Offline mode: nothing leaves this device';b.style.cssText='position:fixed;left:50%;bottom:96px;transform:translateX(-50%);z-index:99998;padding:4px 12px;border-radius:999px;background:#0A1F44;color:#FFD166;font:700 12px Poppins,sans-serif;box-shadow:0 2px 8px #0006;pointer-events:none;white-space:nowrap';document.documentElement.appendChild(b);});
})();
