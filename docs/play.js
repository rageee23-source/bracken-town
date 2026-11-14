let metricsURL,queued=[];
const originTag=new URLSearchParams(location.search).get('source')||'direct';
const session=crypto.randomUUID().replaceAll('-','');
fetch('counter.json',{cache:'no-store'}).then(r=>r.json()).then(c=>{metricsURL=c.url;queued.forEach(signal);queued=[]}).catch(()=>{});
function signal(step){if(!metricsURL){queued.push(step);return}fetch(metricsURL+'/play',{method:'POST',body:JSON.stringify({round:1,source:originTag,session,step}),keepalive:true}).catch(()=>{})}
