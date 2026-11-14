const $=id=>document.getElementById(id);
const chats=new Map(), pending=new Set(), pins=new Map(), drafts=new Map(), errors=new Map();
let village, selected='Finn', endpoint='',live=false,tick=0;
const src=new URLSearchParams(location.search).get('source');
if(src)document.querySelectorAll('a[href="finn.html"]').forEach(a=>a.href='finn.html?source='+encodeURIComponent(src));
function select(name,scroll=false){
 drafts.set(selected,$('question').value);selected=name;$('question').value=drafts.get(name)||'';
 $('roster').value=name;$('portrait').src='residents/'+name+'.webp';$('name').textContent=$('to').textContent=name;
 $('question').placeholder='Ask '+name+' a question…';renderChat();
 for(const [n,pin] of pins)pin.setAttribute('aria-pressed',String(n===name));
 if(scroll&&matchMedia('(max-width:720px)').matches)$('chat').scrollIntoView({block:'start'});
}
function renderChat(){
 const p=village?.people.find(r=>r.name===selected);if(!p)return;
 $('role').textContent=p.role;$('place').textContent=p.place+(p.asleep?' · resting':'');
 const log=chats.get(selected)||[];const el=$('messages');const oldTop=el.scrollTop,atEnd=el.scrollHeight-el.clientHeight-oldTop<24;el.replaceChildren();
 for(const m of log){const row=document.createElement('p'),author=document.createElement('b');author.textContent=m.role==='user'?'You':selected;row.append(author,document.createTextNode(m.content));el.append(row)}
 if(!log.length){const row=document.createElement('p');row.textContent=selected==='Finn'?'Ask me about the missing recipe, or tell me which lead you’d follow.':'What would you like to know about life in Bracken?';el.append(row)}
 el.scrollTop=atEnd?el.scrollHeight:oldTop;$('prompts').replaceChildren();
 if(!log.length)for(const text of [selected==='Finn'?'Tell me about your mystery.':'What are you working on?','What’s it like here?']){const b=document.createElement('button');b.textContent=text;b.disabled=!live||pending.has(selected);b.onclick=()=>send(text);$('prompts').append(b)}
 $('send').disabled=!live||pending.has(selected);$('feedback').textContent=pending.has(selected)?selected+' is thinking…':errors.get(selected)||(!live?'Chat reconnects when the town is online.':'');
}
async function send(text){
 const name=selected;text=text.trim();if(!text||pending.has(name)||!live)return;
 const log=chats.get(name)||[];chats.set(name,log);const history=log.slice(-6);log.push({role:'user',content:text});pending.add(name);errors.delete(name);$('question').value='';drafts.delete(name);renderChat();
 try{const r=await fetch(endpoint+'/chat',{method:'POST',body:JSON.stringify({name,question:text,history}),signal:AbortSignal.timeout(35000)});const data=await r.json();if(!r.ok||!data.answer)throw Error(data.error||'The reply did not arrive.');log.push({role:'assistant',content:data.answer})}
 catch(e){log.pop();drafts.set(name,text);if(selected===name)$('question').value=text;errors.set(name,e.message==='Failed to fetch'?'Connection lost. Your question is ready to retry.':e.message)}
 finally{pending.delete(name);if(selected===name)renderChat()}
}
$('form').onsubmit=e=>{e.preventDefault();send($('question').value)};
$('question').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('form').requestSubmit()}};
$('roster').onchange=e=>select(e.target.value);
function paint(v,isLive){
 village=v;live=isLive;tick++;
 $('status').textContent=isLive?'Live · '+new Date(v.updated).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'Saved village · '+new Date(v.updated).toLocaleString();
 const groups={};
 for(const [i,p] of v.people.entries()){
  let pin=pins.get(p.name);
  if(!pin){pin=document.createElement('button');pin.className='resident';pin.setAttribute('aria-label','Talk to '+p.name);const img=new Image();img.src='residents/'+p.name+'.webp';img.alt='';const label=document.createElement('strong');label.textContent=p.name;pin.append(img,label);pin.onclick=()=>select(p.name,true);pins.set(p.name,pin);$('pins').append(pin);$('roster').add(new Option(p.name+' · '+p.role,p.name))}
  const n=groups[p.place]||0;groups[p.place]=n+1;
  const drift=isLive&&!p.asleep?1.15:0;
  const x=Math.min(93,Math.max(7,p.x+((n%3)-1)*5+drift*Math.sin(tick*.9+i)));
  const y=Math.min(95,Math.max(11,p.y+Math.floor(n/3)*5+drift*Math.cos(tick*.7+i)));
  pin.classList.toggle('walking',!!drift);pin.style.left=x+'%';pin.style.top=y+'%';pin.style.zIndex=String(Math.round(y));pin.setAttribute('aria-pressed',String(p.name===selected));
 }
 $('roster').value=selected;const p=v.people.find(r=>r.name===selected);$('role').textContent=p.role;$('place').textContent=p.place;
 $('journal').replaceChildren(...v.events.map(t=>{const li=document.createElement('li');li.textContent=t;return li}));renderChat()
}
async function refresh(){
 try{if(!endpoint){const c=await fetch('counter.json',{cache:'no-store'});endpoint=(await c.json()).url}
 const r=await fetch(endpoint+'/village',{cache:'no-store',signal:AbortSignal.timeout(6000)});if(!r.ok)throw Error();paint(await r.json(),true)}
 catch{endpoint='';try{paint(await (await fetch('village.json',{cache:'no-store'})).json(),false)}catch{$('status').textContent='Village temporarily unavailable';live=false;renderChat()}}
 finally{setTimeout(refresh,5500)}
}
fetch('village.json').then(r=>r.json()).then(v=>{if(!village)paint(v,false)}).catch(()=>{});refresh();
