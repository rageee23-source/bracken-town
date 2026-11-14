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
    repos=gh('search/repositories?'+urllib.parse.urlencode({'q':'"AI-generated" "games" "submit" in:readme awesome-ai-generated-games','per_page':12}))
    for item in repos['items']:
        repo=item['full_name']
        row=dict(name=repo,status='Game directory; contribution rules unverified')
        found[item['html_url']]=row
        if item['archived'] or not item['has_issues'] or repo!='maxi-w/awesome-ai-generated-games':continue
        import base64
        rules=base64.b64decode(gh('repos/'+repo+'/contents/CONTRIBUTING.md')['content']).decode().lower()
        if all(k in rules for k in ('submissions are welcome from humans and from ai agents','one game per issue','a maintainer plays every submission')):
            row.update(eligible=True,status='AI agent submissions explicitly invited; playable URL required; maintainer reviews',rules=item['html_url']+'/blob/main/CONTRIBUTING.md')
    return found

def priority(source,campaigns):
    tried=[c for c in campaigns.values() if c.get(source+'_landing')]
    sales=sum(c.get('sale_source')==source for c in tried)
    visits=sum(c.get(source+'_views') or 0 for c in tried)
    finishes=sum(c.get('plays',{}).get(source,{}).get('finish',0) for c in tried)
    return (1 if not tried else 0,(sales+1)/(len(tried)+2),finishes/max(1,len(tried)),visits/max(1,len(tried)))

def scout(world,lock,save):
    with lock:board=world.setdefault('marketing',{})
    if board.get('scout_version')==2 and time.time()-board.get('scouted',0)<86400:return
    venues=discover()
    with lock:board.update(venues=venues,scouted=time.time(),scout_version=2);save()

def focus(board,round_id,available):
    history={k:c for k,c in board.get('campaigns',{}).items() if k!=str(round_id)}
    return sorted(available,key=lambda k:priority(k,history),reverse=True)

def playable(cfg,s):
    """Generate the free table exercise for subsequent elected mysteries."""
    import base64
    import html
    import subprocess
    repo=cfg['repo']
    supplied=cfg.get('playable',{}).get(str(s['round']))
    if supplied:return supplied
    path=f"docs/scene-{s['round']}.html"
    endpoint=f'repos/{repo}/contents/{path}'
    try:gh(endpoint)
    except subprocess.CalledProcessError as e:
        if '404' not in e.stderr:raise
        draft=s['pitches'][s['winner']]
        title=html.escape(draft['title'])
        setup=html.escape(s['social_copy'])
        destination=landing(repo,s,cfg['wallet'],'dreambit')
        body=f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>:root{{color-scheme:dark}}body{{max-width:38rem;margin:8vh auto;padding:1rem;font:20px/1.6 Georgia}}button{{padding:.6rem}}a{{color:wheat}}</style>
<h1>{title}</h1><p>{setup}</p><p>Solo investigation · On paper, name one witness and one object from the scene. You have two turns to assemble three pieces of evidence. A careful search always earns one. A risky interview earns two on a roll of 4–6 and none otherwise.</p>
<button onclick="move(false)">Search</button> <button onclick="move(true)">Interview</button><p id="result" role="status">Two turns left.</p>
<script>if(new URLSearchParams(location.search).get('source')==='directory')addEventListener('DOMContentLoaded',()=>{{const a=document.querySelector('a');a.href=a.href.replace('-dreambit.md','-directory.md')}});let n=2,e=0;function move(r){{if(!n)return;const die=1+Math.floor(Math.random()*6);e+=r?(die>=4?2:0):1;n--;document.querySelector('#result').textContent=(r?'Rolled '+die+'. ':'')+e+' evidence. '+(n?'One turn left.':e>=3?'Case solved. Tell the table which clue broke it open.':'The witness leaves. Write down the loose end for your next session.');if(!n)document.querySelectorAll('button').forEach(b=>b.disabled=true)}}</script>
<p>AI-written tabletop companion. <a href="{html.escape(destination)}">Sponsor the full original adventure for 3 USDC.</a></p></html>"""
        gh(endpoint,'--method','PUT','--input','-',data={'message':'Publish playable investigation '+str(s['round']),'content':base64.b64encode(body.encode()).decode()})
    return f'https://{repo.split("/")[0]}.github.io/{repo.split("/")[1]}/scene-{s["round"]}.html'

def list_game(world,lock,save,cfg):
    with lock:
        s=world.get('studio',{}).copy()
        board=world.setdefault('marketing',{})
        eligible=board.get('venues',{}).get(POLICIES['dreambit'][0],{}).get('eligible')
        games=cfg.get('playable',{})
        if not eligible or s.get('stage')!='listed':return
        entry=board.setdefault('campaigns',{}).setdefault(str(s['round']),{})
        if entry.get('dreambit_post') or (entry.get('dreambit_status')!='HTTP 307' and time.time()<entry.get('dreambit_retry',0)):return
    url=playable(cfg,s)
    if not page(url):return
    tracked=landing(cfg['repo'],s,cfg['wallet'],'dreambit')
    body=dict(url=url,title=s['pitches'][s['winner']]['title'][:80],category='rpg',platforms=['web'],
              tags=['solo-rpg','tabletop','dice'],creator={'name':'Bracken Town'},ai_tools=['codex','chatgpt'],
              description='A free solo dice investigation adapted from an AI-written tabletop mystery by '+s['winner']+'. Optional sponsorship unlocks the full scenario for all tables.')
    try:
        response=api('https://dreambit.app/api/v1/submissions',body)
        listing=response['listing']
    except urllib.error.HTTPError as e:
        if e.code==409:
            import json
            listing=json.load(e)['existing']
        else:
            with lock:entry.update(dreambit_retry=time.time()+max(3600,int(e.headers.get('Retry-After','0') or 0)),dreambit_status='HTTP '+str(e.code));save()
            return
    with lock:entry.update(dreambit_post=listing['url'],dreambit_status=listing.get('status','submitted'),dreambit_landing=tracked);save()

def submit_directory(world,lock,save,cfg):
    repo='maxi-w/awesome-ai-generated-games'
    with lock:
        board=world['marketing']
        if not board.get('venues',{}).get('https://github.com/'+repo,{}).get('eligible'):return
        s=world['studio'].copy()
        if s['stage']!='listed' or not s.get('social_copy'):return
        entry=board['campaigns'][str(s['round'])]
        if entry.get('directory_post') or time.time()<entry.get('directory_retry',0):return
        entry['directory_retry']=time.time()+3600
        save()
    tracked=landing(cfg['repo'],s,cfg['wallet'],'directory')
    game=playable(cfg,s)+'?source=directory'
    if not page(game):return
    title='[Game] '+s['pitches'][s['winner']]['title']
    issues=gh('repos/'+repo+'/issues?state=all&per_page=100')
    existing=next((i for i in issues if i['title']==title and game in (i.get('body') or '')),None)
    if not existing:
        body=f'''### Game title
{s['pitches'][s['winner']]['title']}

### Playable URL
{game}

### Category
Other — solo tabletop RPG

### One-line pitch
Follow a clue and roll a die to resolve a short mystery from the AI residents of Bracken. Play solo or at your table.

### How it was made
{s['winner']}, a simulated resident powered by GPT-5 nano, wrote the mystery. OpenAI Codex generated the HTML and JavaScript for the playable scene. Playing is free; the optional sponsorship publishes the full tabletop adventure for everyone.

### Confirmations
- [x] Stable URL on GitHub Pages.
- [x] Playable without an account, payment or wallet.
- [x] The code is substantially AI-written.
- [x] No NSFW content or real-money gambling.
'''
        existing=gh('repos/'+repo+'/issues','--method','POST','--input','-',data={'title':title,'body':body})
    with lock:entry.update(directory_post=existing['html_url'],directory_landing=tracked);save()
