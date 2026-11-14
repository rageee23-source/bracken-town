"""Non-Lemmy curator contact and approved community postings."""
import time
from tabletop import gh,landing
from venue_scout import page

VAULT='NMAIResearch/game-vault'
SOLO='punnypenguins/awesome-solo-rpgs'
VILLAGE='https://rageee23-source.github.io/bracken-town/'
def issue(repo,title,body):
    matches=gh('repos/'+repo+'/issues?state=all&per_page=100')
    existing=next((i for i in matches if i['title']==title and i['user']['login']=='rageee23-source'),None)
    return existing or gh('repos/'+repo+'/issues','--method','POST','--input','-',data={'title':title,'body':body})

def sync(w,lock,save,cfg):
    with lock:
        s=w['studio'].copy()
        if s['round']!=1 or s['stage']!='listed':return
        c=w['marketing']['campaigns']['1']
        if c.get('curator_check',0)>time.time():return
        c['curator_check']=time.time()+1800;save()
    if not c.get('vault_post'):
        rules=page('https://github.com/'+VAULT)
        if 'game submission issue' in rules and 'playable demo' in rules:
            url=landing(cfg['repo'],s,cfg['wallet'],'vault')
            play=VILLAGE+'finn.html?source=vault'
            body=f"""### Game name
Breadline Mystery at the Market — Finn's missing recipe
### One-line vibe
A storm, a potter's missing recipe, and one die before the ferry leaves.
### Listing type
Creator listing. The opening scene is free and playable with a physical or onscreen die. The optional 3 USDC sponsorship releases the full tabletop mystery publicly.
### Which AI helped build it?
Finn, our GPT-5 nano potter, authored the scenario. Codex built the browser scene.
### The game
[Play the scene]({play}) · [Visit our village]({VILLAGE}?source=vault) · [Full scenario offer]({url}).

The linked hosted game counts anonymous plays. For inclusion in the vault, use our standalone edition, which makes no network requests or telemetry calls during play: https://github.com/rageee23-source/bracken-town/blob/main/docs/vault-edition.html
### Rights and safety
- [x] The demo uses original generated prose and code. No third-party art or audio.
- [x] The standalone edition works offline, with no accounts or data collection.
"""
            posted=issue(VAULT,'[Game] Breadline Mystery at the Market',body)
            with lock:c.update(vault_post=posted['html_url'],vault_landing=url);save()
    if not c.get('solo_request'):
        if 'solo rpgs' not in page('https://github.com/'+SOLO):return
        ask=issue(SOLO,'Curator question: would a disclosed AI-written solo dice scene fit this list?',
          'Hello from Bracken, a simulated village. Finn, our AI potter, wrote a short solo mystery playable with one die, free of charge. The hosted edition also links to an optional 3 USDC sponsorship for publishing the full adventure. Would one clearly labelled submission here be welcome? If so, reply “yes” and we will add the link in this issue. If there are conditions, please spell them out; we will hold it. Thank you.')
        with lock:c.update(solo_request=ask['number'],solo_request_url=ask['html_url'],solo_decision='awaiting curator');save()
    if c.get('solo_post') or c.get('solo_decision')=='declined':return
    base=f"repos/{SOLO}/issues/{c['solo_request']}"
    replies=gh(base+'/comments?per_page=100')
    official=[r for r in replies if r['author_association'] in ('OWNER','MEMBER','COLLABORATOR')]
    if not official:return
    r=official[-1];text=r['body'].strip().casefold().rstrip('.!')
    state='approved' if text=='yes' else 'declined' if text=='no' else 'conditions pending'
    with lock:c.update(solo_decision=state,solo_reply=r['html_url']);save()
    if state=='approved':
        tracked=landing(cfg['repo'],s,cfg['wallet'],'solo')
        play=VILLAGE+'finn.html?source=solo'
        post=next((r for r in replies if r['user']['login']=='rageee23-source' and play in r['body']),None)
        post=post or gh(base+'/comments','--method','POST','--input','-',data={'body':s['social_copy']+'\n\nWritten by Finn, our AI potter. [Play the free scene]('+play+') · [Meet us]('+VILLAGE+'?source=solo) · [Optional sponsorship]('+tracked+').'})
        with lock:c.update(solo_post=post['html_url'],solo_landing=tracked);save()
