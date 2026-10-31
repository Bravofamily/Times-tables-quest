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
 /* v33: the badge is a full-width strip docked just above the bottom tab bar (or the screen bottom when there is none), with a spacer at the end of the page, so it never covers cards */
 document.addEventListener('DOMContentLoaded',function(){var b=document.createElement('div');b.id='nrOfflineBadge';b.setAttribute('role','status');b.textContent='📴 Offline mode: nothing leaves this device';b.style.cssText='position:fixed;left:0;right:0;bottom:0;z-index:99998;padding:6px 12px;text-align:center;background:#0A1F44;color:#FFD166;font:700 12px/16px Poppins,sans-serif;box-shadow:0 -2px 8px #0006;pointer-events:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis';document.documentElement.appendChild(b);
  var sp=document.createElement('div');sp.id='nrOfflineSpacer';sp.setAttribute('aria-hidden','true');document.body.appendChild(sp);
  function place(){try{var n=document.getElementById('bnav'),h=0;if(n){var r=n.getBoundingClientRect(),cs=getComputedStyle(n);if(cs.display!=='none'&&cs.visibility!=='hidden'&&r.height>0&&r.bottom>=window.innerHeight-2)h=Math.round(window.innerHeight-r.top);}b.style.bottom=h+'px';sp.style.height=(b.offsetHeight+4)+'px';if(sp.parentNode!==document.body||document.body.lastElementChild!==sp)document.body.appendChild(sp);}catch(e){}}
  place();addEventListener('resize',place);addEventListener('load',place);setInterval(place,1000);});
})();
