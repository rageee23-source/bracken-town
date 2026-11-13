import json, os, time, threading, uuid, urllib.request, urllib.error
from pathlib import Path
import economy, budget, council, studio, sales, marketing, town_accounts
from needs import FACILITIES, initialize, advance, resolve
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT=Path(__file__).resolve().parent
SAVE=ROOT/'town.json'
ADDR='127.0.0.1:8798'
MODEL='gpt-5-nano'
PLACES={'Market':[24,31],'Library':[56,31],'Orchard':[78,30],'Square':[47,55],'Workshop':[24,76],'Bakery':[54,85],'Riverbank':[78,63],'Town Hall':[27,52],'Church':[70,15]}
GATHERINGS={'Town Hall':'Open assembly for meeting neighbors, sharing news and planning joint projects.','Church':'A quiet chapel for reflection, music and candlelit gatherings.'}
PEOPLE=[
 ('Alma','Botanist','Find a way to grow pears on the riverbank.','#657c43'),
 ('Otto','Clockmaker','Build a clock the town can hear across the water.','#bd673f'),
 ('Nell','Baker','Invent a loaf using something grown nearby.','#aa7840'),
 ('Ivo','Ferryman','Collect the best story told at every landing.','#467c95'),
 ('Bea','Archivist','Find a missing page of the town history.','#996680'),
 ('Sol','Carpenter','Build a bench where strangers will meet.','#7c7355'),
 ('Ada','Musician','Gather players for an evening concert.','#b55c54'),
 ('Finn','Potter','Find a new glaze color in the landscape.','#7568a0'),
 ('Mira','Cartographer','Map the footpaths residents actually use.','#4c8e81'),
 ('Pip','Apprentice','Discover a craft worth learning.','#947535')]
LOCK=threading.RLock()
def fresh():
    places=list(PLACES)
    return dict(running=True,epoch=0,cursor=0,requests=0,cost=0,warning='',minutes=420,events=[],residents=[
      dict(name=n,role=r,goal=g,color=c,place=places[i%len(places)],memory=[],turns=0) for i,(n,r,g,c) in enumerate(PEOPLE)])
world=json.loads(SAVE.read_text('utf8')) if SAVE.exists() else fresh()
initialize(world["residents"])
economy.setup(world)
budget.treasury(world)
if world.pop('allowance',None) is not None and world.get('warning'):
    world.update(running=True,warning='')
world.setdefault('retry_at',0)
world.setdefault('failures',0)
def save():
    f=SAVE.with_suffix('.tmp')
    f.write_text(json.dumps(world,ensure_ascii=False),'utf8');f.replace(SAVE)
def choose(actor,neighbors,minute):
    prompt={'you':actor['name'],'power_reserve':world['economy']['grid']['stored'],'coins':actor['coins'],'pantry':actor['pantry'],'job_at':actor['job_place'],'plot_ready_minute':actor['crop_ready'],'market':world['economy']['listings'],'public_payroll':world['economy']['treasury'],'occupation':actor['role'],'current_goal':actor['goal'],'here':actor['place'],'people_here':neighbors,'places':list(PLACES),'gathering_places':{place:{'purpose':purpose,'currently_here':[p['name'] for p in world['residents'] if p['place']==place]} for place,purpose in GATHERINGS.items()},'reserves_out_of_100':actor['needs'],'facilities':FACILITIES,'awake_people_by_place':{place:[p['name'] for p in world['residents'] if p['place']==place and p['sleep_until']<=minute and p['name']!=actor['name']] for place in PLACES},'recent_memories':actor['memory'][-6:],'town_minute':minute}
    instructions=('You are one autonomous resident of Bracken, a fictional riverside town. Choose your next move independently. You may stay, walk anywhere listed, rest, make something, seek company or change your goal. Generate at Riverbank when the power reserve falls below 12; this produces 18 units and pays up to 4 coins. Town demand uses one unit per tick; exports above the elected reserve pay the town and owner. Choose among generate, work, plant, harvest, sell, buy, eat, drink, sleep, socialize and pursue. Work your trade for 4 fictional coins from the treasury; bakers also get bread. Anyone can plant a free allotment, harvest 5 vegetables after 160 town minutes, list pantry food for sale, or buy one serving from a stall. Aim to have a meal in reserve. Grow or earn when supplies run low; choose when to trade. Eating consumes pantry food, buys food if needed or forages a smaller meal. Match your destination to its facilities. For company choose an awake neighbor at the destination. Below 40 prioritize a low reserve; at night favor sleep if tired. Pursue lets you freely work, explore or rest informally without replenishing reserves. Only speak to people present before moving; their reply belongs to them. Keep continuity. Return JSON with destination (exact place), action (concrete third-person past-tense sentence, max 140 characters), say (optional short spoken words before departure), goal (your continuing or new aim).')
    body={'model':MODEL,'reasoning_effort':'minimal','max_completion_tokens':650,'response_format':{'type':'json_schema','json_schema':{'name':'town_decision','strict':True,'schema':{'type':'object','properties':{'activity':{'type':'string','enum':economy.ECON_ACTIONS+['drink','sleep','socialize','pursue']},'destination':{'type':'string','enum':list(PLACES)},'action':{'type':'string'},'say':{'type':'string'},'goal':{'type':'string'}},'required':['activity','destination','action','say','goal'],'additionalProperties':False}}},'messages':[{'role':'system','content':instructions},{'role':'user','content':json.dumps(prompt)}]}
    motion=council.session(world)
    if motion and actor['name'] not in motion['ballots']:
        body['messages'][0]['content'] += ' Cast your own yes or no town hall vote given your occupation, goals, and town needs. Motion: '+motion['text']
        schema=body['response_format']['json_schema']['schema']
        schema['properties']['vote']={'type':'string','enum':['yes','no']}
        schema['required'].append('vote')
    body['messages'][1]['content'] += ' Town marketing results (repository traffic is aggregate): '+json.dumps({'traffic':world.get('marketing',{}).get('repo_views_14d'),'campaigns':list(world.get('marketing',{}).get('campaigns',{}).values())[-3:],'confirmed_sales':len(world.get('commissions',[]))})
    assignment=studio.task(world,actor)
    if assignment:
        kind,instruction=assignment
        body['messages'][0]['content']+=' At the town hall: '+instruction
        schema=body['response_format']['json_schema']['schema']
        for field in (['pitch','manuscript'] if kind=='pitch' else ['social_copy'] if kind=='promote' else ['selection']):
            schema['properties'][field]={'type':'string'}
            schema['required'].append(field)
    if len(json.dumps(body).encode())>65536:raise ValueError('Request size limit')
    req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=40) as resp: result=json.load(resp)
    usage=result['usage']
    return result['choices'][0]['message']['content'],(usage['prompt_tokens']*.05+usage['completion_tokens']*.4)/1e6
def cycle():
    with LOCK:
        if not world['running']:return False
        b=budget.treasury(world)
        idx=world['cursor']%10;a=world['residents'][idx];before=a['place'];actor=json.loads(json.dumps(a))
        if a['sleep_until']>world['minutes']:
            economy.grid_tick(world)
            advance(world['residents'],world['minutes'])
            world['minutes']+=4;world['cursor']+=1;save();return True
        neighbors=[p['name'] for p in world['residents'] if p is not a and p['place']==before and p['sleep_until']<=world['minutes']]
        epoch=world['epoch'];minute=world['minutes']
        key=bool(os.getenv('OPENAI_API_KEY'))
        paid=key and time.time()>=world['retry_at'] and budget.reserve(b)
        if paid:
            world['requests']+=1
            save()
    source='Local';warning=''
    k=min(actor['needs'],key=actor['needs'].get)
    activity=({'food':'eat','water':'drink','energy':'sleep','company':'socialize'}[k] if actor['needs'][k]<42 else
              'generate' if world['economy']['grid']['stored']<12 else
              'plant' if actor['crop_ready'] is None else
              'harvest' if actor['crop_ready']<=minute else
              'sell' if actor['pantry']['vegetables']>1 else 'work')
    decision=dict(activity=activity,destination=before,action='',goal=actor['goal'],say='')
    if paid:
        try:
            raw,cost=choose(actor,neighbors,minute)
            with LOCK:
                budget.settle(b,cost);world['cost']+=cost
            candidate=json.loads(raw)
            if (candidate['destination'] not in PLACES or candidate['activity'] not in economy.ECON_ACTIONS+['drink','sleep','socialize','pursue']
                or not all(isinstance(candidate[k],str) for k in ('goal','action','say')) or not candidate['goal'].strip() or not candidate['action'].strip()):
                raise ValueError('Invalid decision')
            decision=candidate;source='OpenAI';world.update(failures=0,retry_at=0)
        except Exception as e:
            # If delivery or billing is unknown the pre-call hold stays charged to the cap.
            world['failures']=min(8,world['failures']+1)
            world['retry_at']=time.time()+min(3600,30*2**world['failures'])
            warning='Local decisions while OpenAI recovers; retry scheduled.'
    else:
        warning=('Operating funds exhausted; local decisions continue.' if b['spent']+b['held']+budget.RESERVE>budget.limit(b)
                 else 'Local decisions while waiting for OpenAI.' if key else 'Local decisions; API key unavailable.')
    dest=decision['destination'];action=decision['action'];goal=decision['goal'];say=decision['say']
    try:
        with LOCK:
            if epoch==world['epoch']:
                studio.record(world,a,decision,source)
                motion=council.session(world)
                if motion:
                    if source=='OpenAI':
                        ballot=decision.get('vote')
                    else:
                        # When offline, residents with funded trades favor earlier exports.
                        favors_exports=a['job_place'] in ('Workshop','Market','Bakery') or a['coins']<6
                        ballot='yes' if favors_exports==(motion['target']==12) else 'no'
                    council.vote(world,a,ballot,source)
                dest,action,activity=resolve(a,world['residents'],minute,decision,world)
                if activity and (dest!=decision['destination'] or activity!=decision['activity']):say=''
                event=dict(source=source,activity=activity or 'pursue',id=uuid.uuid4().hex,name=a['name'],start=before,end=dest,action=action[:220],say=say[:180],minute=minute)
                world['events']=(world['events']+[event])[-200:]
                for p in world['residents']:
                    if p is a or (p['sleep_until']<=minute and p['place']==dest):
                        p['memory']=(p['memory']+[event['action']])[-16:]
                a.update(place=dest,goal=goal[:220],turns=a['turns']+1)
                economy.grid_tick(world)
                advance(world['residents'],minute)
                world.update(cursor=world['cursor']+1,minutes=minute+4,warning=warning)
            save()
    except Exception as e:
        with LOCK:
            world.update(warning='Town turn could not complete; retrying.');save()
    return True
def loop():
    while True:
        try:
            worked=cycle()
        except Exception:
            with LOCK:
                world['warning']='Turn interrupted. The town will retry.'
            worked=True
        opening_assembly=world.get('studio',{})
        launching=(opening_assembly.get('round')==1 and opening_assembly.get('stage') in ('pitch','vote'))
        time.sleep((2 if world['cursor']<10 or launching else 20) if worked else 1)
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def respond(self,status,body,mime='application/json'):
        if not isinstance(body,bytes):body=json.dumps(body).encode()
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Frame-Options','DENY');self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.headers.get('Host')!=ADDR:return self.respond(403,{})
        if self.path=='/api/town':
            with LOCK:
                b=budget.treasury(world)
                public_budget={k:v for k,v in b.items() if k!='receipts'}
                public_budget.update(limit=budget.limit(b),net_cents=sum(b['receipts'].values()))
                return self.respond(200,{**world,'budget':public_budget,'places':PLACES,'facilities':FACILITIES,'model':MODEL})
        assets={'/':('index.html','text/html; charset=utf-8'),'/town.js':('town.js','text/javascript'),'/town.css':('town.css','text/css'),'/map.svg':('map.svg','image/svg+xml')}
        if self.path not in assets:return self.respond(404,{})
        file,mime=assets[self.path];self.respond(200,(ROOT/'public'/file).read_bytes(),mime)
    def do_POST(self):
        if self.headers.get('Origin')!='http://'+ADDR or self.headers.get('Host')!=ADDR:return self.respond(403,{})
        if self.path=='/api/settlement':
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<=1024:raise ValueError('Invalid request size.')
                data=json.loads(self.rfile.read(size))
                with LOCK:
                    budget.receive(budget.treasury(world),data['reference'],data['net_usd_cents'])
                    save()
                return self.respond(200,{'ok':True})
            except (ValueError,KeyError,TypeError) as error:
                return self.respond(400,{'error':str(error)})
        if self.path not in ['/api/pause','/api/resume']:return self.respond(404,{})
        with LOCK:
            if self.path.endswith('pause'):
                world.update(running=False,epoch=world['epoch']+1)
            else:
                world.update(running=True,warning='')
            save()
        self.respond(200,{'ok':True})
def storefront():
    config_path=ROOT/'store.local.json'
    if not config_path.exists():return
    cfg=json.loads(config_path.read_text('utf-8-sig'))
    while True:
        try:
            sales.update(world,LOCK,save,cfg)
            with LOCK:world.pop('store_error',None)
        except Exception as error:
            with LOCK:world['store_error']='Store retry scheduled ('+type(error).__name__+').'
        try:
            if cfg.get('tabletop'):
                import venue_scout
                try:
                    venue_scout.scout(world,LOCK,save)
                except Exception as error:
                    with LOCK:world['scout_error']=type(error).__name__
                with LOCK:
                    campaign=world.setdefault('marketing',{}).setdefault('campaigns',{}).setdefault(str(world['studio']['round']),{})
                    channels=['forum','nostr']
                    if world['marketing'].get('venues',{}).get(venue_scout.POLICIES['dreambit'][0],{}).get('eligible'):
                        channels.insert(0,'dreambit')
                    if world['marketing'].get('venues',{}).get('https://github.com/maxi-w/awesome-ai-generated-games',{}).get('eligible'):
                        channels.insert(0,'directory')
                    order=venue_scout.focus(world['marketing'],world['studio']['round'],channels)
                    campaign['focus']=order
                if 'directory' in order[:2]:
                    venue_scout.submit_directory(world,LOCK,save,cfg)
                if 'dreambit' in order[:2]:
                    venue_scout.list_game(world,LOCK,save,cfg)
            if cfg.get('forum') and (not cfg.get('tabletop') or 'forum' in order[:2] or campaign.get('forum')):
                town_accounts.sync_forum(world,LOCK,save,cfg['forum'])
            marketing.sync(world,LOCK,save,cfg['repo'])
            with LOCK:world.pop('marketing_error',None)
        except Exception as error:
            with LOCK:world['marketing_error']='Marketing retry pending ('+type(error).__name__+').'
        if cfg.get('tabletop'):
            try:
                import tabletop
                tabletop.sync(world,LOCK,save,cfg)
                with LOCK:world.pop('tabletop_error',None)
            except Exception as error:
                with LOCK:world['tabletop_error']='Tabletop outreach retry pending ('+type(error).__name__+').'
        if cfg.get('tabletop'):
            try:
                import mod_outreach
                mod_outreach.poll(world,LOCK,save,cfg)
                with LOCK:world.pop('moderation_error',None)
            except Exception as error:
                with LOCK:world['moderation_error']='Moderator inbox retry pending ('+type(error).__name__+').'
        time.sleep(60)

if __name__=='__main__':
    http=ThreadingHTTPServer(('127.0.0.1',8798),Handler)
    threading.Thread(target=loop,daemon=True).start()
    threading.Thread(target=storefront,daemon=True).start()
    http.serve_forever()
