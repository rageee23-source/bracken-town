const $=id=>document.getElementById(id);
function el(tag,txt){const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;return e}
let town,selected='Alma',logKey='',busy=false;
const hour=m=>new Date((m%1440)*60000).toISOString().slice(11,16);
let clearings={};
function art(){const img=el('span');img.className='avatar-art';img.setAttribute('aria-hidden','true');return img}
function showPlaces(places){
 if(Object.keys(clearings).length)return;
 clearings=places;
 for(const [name,[x,y]] of Object.entries(clearings)){
 const label=el('span',name);label.className='place-label';label.style.left=x+'%';label.style.top=(y+3.6)+'%';$('map').append(label);
}
}
function detail(){
 const p=town.residents.find(r=>r.name===selected);
 const box=$('detail');box.dataset.name=p.name;const role=el('small',p.role+' · '+p.place),label=el('small','Latest memory');role.className='occupation';label.className='memory-title';box.replaceChildren(art(),el('h3',p.name),role,el('p',p.goal),label,el('p',p.memory.at(-1)||'Just arrived in town.'));
 const needs=el('section');needs.className='needs';needs.setAttribute('aria-label','Resident needs');
 const labels={food:'Food',water:'Water',energy:'Energy',company:'Company'};
 for(const [key,value] of Object.entries(p.needs||{})){
  const row=el('label',labels[key]);const meter=el('meter');meter.min=0;meter.max=100;meter.low=35;meter.high=65;meter.optimum=90;meter.value=value;
  row.append(meter,el('span',Math.round(value)+'%'));needs.append(row);
 }
 if(p.sleep_until>town.minutes)needs.prepend(el('strong','Sleeping until '+hour(p.sleep_until)));
 box.insertBefore(needs,label);
 const plot=p.crop_ready==null?'No crop planted':town.minutes>=p.crop_ready?'Crop ready to harvest':'Crop ready in '+(p.crop_ready-town.minutes)+' town minutes';
 const possessions=el('p',p.coins+' coins · '+p.pantry.bread+' bread · '+p.pantry.vegetables+' vegetables');possessions.append(el('br'),el('small','Workplace: '+p.job_place+' · '+plot));box.insertBefore(possessions,label);
 for(const e of document.querySelectorAll('button[data-name]')){e.classList.toggle('selected',e.dataset.name===selected);e.setAttribute('aria-pressed',String(e.dataset.name===selected));}
}
function select(name){selected=name;detail()}
function journal(){
 const who=$('filter').value,key=who+(town.events.at(-1)?.id||'empty');
 if(key===logKey)return;logKey=key;
 const events=town.events.filter(e=>!who||e.name===who).reverse().slice(0,45);
 const rows=events.map(e=>{const r=el('div');r.className='event';const text=el('div');text.append(el('strong',e.name+(e.source==='Local'?' (local)':'')+' · '+(e.start===e.end?e.end:e.start+' → '+e.end)),el('p',e.action));if(e.say)text.append(el('q',e.say));r.append(el('time',hour(e.minute)),text);return r});
 $('events').replaceChildren(...(rows.length?rows:[el('p','Waiting for the first decision…')]));
}
function render(){
 showPlaces(town.places);
 const econ=town.economy;
 $('grid').textContent='River power: '+econ.grid.stored+' units stored · '+econ.grid.exported+' exported · '+econ.grid.unserved+' unmet. Your tax account: '+econ.grid.owner+' town coins.';
 $('market').replaceChildren(el('p','Public payroll: '+econ.treasury+' coins'),...econ.listings.map(o=>el('p',o.seller+' · '+o.quantity+' '+o.item+' · '+o.price+' coins each')),el('strong','Recent transactions'),...econ.ledger.slice(-4).reverse().map(l=>el('p',hour(l.minute)+' · '+l.text)));
 if(!econ.ledger.length)$('market').append(el('p','No transactions yet.'));

 if(!$('facilities').childElementCount){for(const [place,services] of Object.entries(town.facilities||{})){
  const line=el('p');line.append(el('b',place+' - '),document.createTextNode(Object.values(services).join(', ')));$('facilities').append(line)
 }$('facilities').append(el('p','Residents can socialize anywhere an awake neighbor is present.'));}

 $('clock').textContent='Day '+(1+Math.floor(town.minutes/1440))+' · '+hour(town.minutes);
 $('state').textContent=town.running?'Live':'Paused';$('pause').textContent=town.running?'Pause town':'Resume town';$('pause').disabled=busy;
 $('model').textContent='10 independent residents · '+town.model;
 const b=town.budget;
 $('budget').textContent='$'+Math.max(0,b.limit-b.spent-b.held).toFixed(4)+' available · $'+b.seed+' one-time seed · $'+b.spent.toFixed(4)+' API spend · $'+b.held.toFixed(4)+' held · $'+(b.net_cents/100).toFixed(2)+' settled revenue · $'+(b.owner_cents/100).toFixed(2)+' owner share accrued';
 const hall=town.hall, motion=hall?.motion, last=hall?.history.at(-1);
 $('hall').textContent=(motion?motion.text+' '+Object.entries(motion.ballots).map(([name,v])=>name+' '+v.vote+' ('+v.source+')').join(', '):'Assembly adjourned.')+(last?' Last motion '+(last.passed?'passed':'failed')+' — '+last.text:'');
 $('error').textContent=town.warning;
 town.residents.forEach((p,i)=>{
  let pin=$('pin'+i);if(!pin){pin=el('button');const tag=el('span',p.name);tag.className='tag';pin.append(tag);pin.id='pin'+i;pin.className='pin';pin.dataset.name=p.name;pin.onclick=()=>select(p.name);pin.style.setProperty('--c',p.color);$('pins').append(pin);
   const person=el('button');person.dataset.name=p.name;person.className='person';person.onclick=()=>select(p.name);const avatar=el('span');avatar.className='portrait';avatar.append(art());avatar.style.setProperty('--c',p.color);const words=el('span');words.append(el('b',p.name),el('small',p.role));person.append(avatar,words);$('people').append(person);$('filter').add(new Option(p.name,p.name));
  }
  const group=town.residents.filter(r=>r.place===p.place),j=group.findIndex(r=>r.name===p.name),[x,y]=clearings[p.place];
  if(pin.dataset.place && pin.dataset.place!==p.place){pin.classList.remove('walking');void pin.offsetWidth;pin.classList.add('walking')}pin.dataset.place=p.place;
  pin.style.left=(x+(j%4-(Math.min(4,group.length)-1)/2)*5.4)+'%';pin.style.top=(y+Math.floor(j/4)*5.5)+'%';pin.title=p.name+' at '+p.place;pin.setAttribute('aria-label',pin.title);
 });detail();journal()
}
async function refresh(){try{const r=await fetch('/api/town');if(!r.ok)throw Error();town=await r.json();render()}catch{$('state').textContent='Disconnected';$('pause').disabled=true}}
$('filter').onchange=journal;$('pause').onclick=async()=>{if(busy)return;busy=true;$('pause').disabled=true;try{await fetch(town.running?'/api/pause':'/api/resume',{method:'POST'})}finally{busy=false;await refresh()}};
refresh();setInterval(refresh,1500);
