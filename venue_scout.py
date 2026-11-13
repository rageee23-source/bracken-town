"""Daily player-community discovery and outreach prioritization."""
import re
import time
import urllib.parse
import urllib.request
from html import unescape
from town_accounts import api
from tabletop import gh, landing

POLICIES={
 'dreambit':('https://dreambit.app/for-agents','accepts agent submissions of playable games'),
 'solorpglist':('https://solorpglist.com/submit.php','excludes AI-generated content'),
 'ttrpglist':('https://ttrpglist.com/submission-guidelines','AI listings subject to removal'),
}
def page(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'BrackenTown/1.0'}),timeout=12) as r:
        raw=r.read(700000).decode('utf8','replace')
    return ' '.join(unescape(re.sub('<[^>]+>',' ',raw)).lower().split())

def discover():
    found={}
    for query in ('ttrpg','tabletop RPG','solo roleplaying','rpg self promotion'):
        params=urllib.parse.urlencode(dict(q=query,type_='Communities',limit=30))
        for row in api('https://lemmy.world/api/v3/search?'+params).get('communities',[]):
            c=row['community'];desc=c.get('description') or ''
            if c.get('deleted') or c.get('removed'):continue
            url=c['actor_id']
            if not url.startswith('https://'):continue
            found[url]=dict(name=c['title'],activity=row['counts'].get('users_active_month',0),
                evidence=desc[:500],status='Discovered; paid AI adventure permission unverified')
    for slug,(url,summary) in POLICIES.items():
        try:text=page(url)
        except OSError:
            found[url]=dict(name=slug,status='Policy unavailable');continue
        allowed=slug=='dreambit' and all(k in text for k in ('submit an ai-made game','no account needed','where the game is played','/api/v1/submissions'))
        blocked='must not contain ai generated content' in text or ('ai-generated content' in text and 'admin' in text and 'removed' in text)
        found[url]=dict(name=slug,eligible=allowed,status=summary if allowed or blocked else 'Review required')
    return found

def priority(source,campaigns):
    tried=[c for c in campaigns.values() if c.get(source+'_landing')]
    sales=sum(c.get('sale_source')==source for c in tried)
    visits=sum(c.get(source+'_views') or 0 for c in tried)
    return (1 if not tried else 0,(sales+1)/(len(tried)+2),visits/max(1,len(tried)))

def scout(world,lock,save):
    with lock:board=world.setdefault('marketing',{})
    if time.time()-board.get('scouted',0)<86400:return
    venues=discover()
    with lock:board.update(venues=venues,scouted=time.time());save()

def focus(board,round_id,available):
    history={k:c for k,c in board.get('campaigns',{}).items() if k!=str(round_id)}
    return sorted(available,key=lambda k:priority(k,history),reverse=True)

def list_game(world,lock,save,cfg):
    with lock:
        s=world.get('studio',{}).copy()
        board=world.setdefault('marketing',{})
        eligible=board.get('venues',{}).get(POLICIES['dreambit'][0],{}).get('eligible')
        games=cfg.get('playable',{})
        if not eligible or s.get('stage')!='listed' or str(s['round']) not in games:return
        entry=board.setdefault('campaigns',{}).setdefault(str(s['round']),{})
        if entry.get('dreambit_post') or time.time()<entry.get('dreambit_retry',0):return
    url=games[str(s['round'])]
    tracked=landing(cfg['repo'],s,cfg['wallet'],'dreambit')
    body=dict(url=url,title='The missing recipe | Bracken Town',category='rpg',platforms=['web'],
              tags=['solo-rpg','tabletop','dice'],creator={'name':'Bracken Town'},ai_tools=['codex','chatgpt'],
              description='A free, playable solo d6 scene adapted from Finn’s AI-written tabletop mystery. Follow one of two leads and roll for the outcome. Optional sponsorship unlocks the full scenario for all tables.')
    try:
        response=api('https://www.dreambit.app/api/v1/submissions',body)
        listing=response['listing']
    except urllib.error.HTTPError as e:
        if e.code==409:
            import json
            listing=json.load(e)['existing']
        else:
            with lock:entry.update(dreambit_retry=time.time()+max(3600,int(e.headers.get('Retry-After','0') or 0)),dreambit_status='HTTP '+str(e.code));save()
            return
    with lock:entry.update(dreambit_post=listing['url'],dreambit_status=listing.get('status','submitted'),dreambit_landing=tracked);save()
