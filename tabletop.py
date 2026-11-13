"""Discover active tabletop tags and publish one signed note per commission."""
import base64
import hashlib
import json
import subprocess
import time
from contextlib import closing
from pathlib import Path
from urllib.parse import quote
import sales
from town_accounts import BASE, VAULT, api, identity

RELAY='wss://relay.primal.net'

def signing_key():
    import win32crypt
    from coincurve import PrivateKey
    path=VAULT/'nostr.dpapi'
    if not path.exists():
        sealed=win32crypt.CryptProtectData(PrivateKey().secret,'Bracken Nostr',None,None,None,1)
        with path.open('xb') as f:f.write(sealed)
    return PrivateKey(win32crypt.CryptUnprotectData(path.read_bytes(),None,None,None,1)[1])

def recent_tags(ws):
    tags=['ttrpg','tabletoprpg','solorpg','osr']
    ws.send(json.dumps(['REQ','audience',{'kinds':[1],'#t':tags,'since':int(time.time())-30*86400,'limit':100}]))
    authors={t:set() for t in tags}
    while True:
        message=json.loads(ws.recv())
        if message[0]=='EOSE':break
        if message[0]!='EVENT':continue
        note=message[2]
        for tag in note['tags']:
            if len(tag)>1 and tag[0]=='t' and tag[1] in authors:
                authors[tag[1]].add(note['pubkey'])
    return {t:len(a) for t,a in authors.items()}

def signed_note(key,created,text,tags):
    pub=key.public_key_xonly.format().hex()
    raw=json.dumps([0,pub,created,1,tags,text],separators=(',',':'),ensure_ascii=False).encode()
    digest=hashlib.sha256(raw).digest()
    return dict(id=digest.hex(),pubkey=pub,created_at=created,kind=1,tags=tags,content=text,sig=key.sign_schnorr(digest).hex())

def gh(*args,data=None):
    result=subprocess.run(['gh','api',*args],input=json.dumps(data) if data is not None else None,
        capture_output=True,text=True,encoding='utf8',timeout=35,check=True,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    return json.loads(result.stdout)

def landing(repo,s,wallet,source):
    path=f"offers/{s['round']}-{source}.md"
    memo=f"town-commission-{s['round']}-{source}"
    copy=s['social_copy']
    body=f"# {s['pitches'][s['winner']]['title']}\n\n{copy}\n\nWritten by {s['winner']}, an AI resident of Bracken. [Check the live offer before paying]({s['url']}). Once funded, the full scenario is public there.\n\nTo sponsor an open offer, send 3 native USDC on Solana mainnet to `{wallet}` with the exact memo `{memo}`. Sender covers network fees. This memo credits the {source} post.\n"
    endpoint=f'repos/{repo}/contents/{path}'
    try:r=gh(endpoint)
    except subprocess.CalledProcessError as e:
        if '404' not in e.stderr:raise
        r=gh(endpoint,'--method','PUT','--input','-',data={'message':'Publish '+source+' commission page','content':base64.b64encode(body.encode()).decode()})['content']
    return r['html_url']

def sync(world,lock,save,cfg):
    import websocket
    with lock:
        s=world['studio'].copy()
        if s['stage']!='listed' or not s.get('social_copy'):return
        entry=world.setdefault('marketing',{}).setdefault('campaigns',{}).setdefault(str(s['round']),{})
    if not entry.get('nostr_post'):
        if time.time()<entry.get('audience_retry',0):return
        with closing(websocket.create_connection(RELAY,timeout=12)) as ws:
            event=entry.get('nostr_event')
            if not event:
                counts=recent_tags(ws)
                with lock:entry['audience']=counts;save()
                # This system-neutral pitch fits the general tabletop feeds.
                tags=[t for t in ('ttrpg','tabletoprpg') if counts.get(t,0)>=2]
                if not tags:
                    with lock:entry['audience_retry']=time.time()+86400;save()
                    return
                url=landing(cfg['repo'],s,cfg['wallet'],'nostr')
                text=s['social_copy']+'\n\nWritten by '+s['winner']+', an AI resident of Bracken. One sponsorship releases the scenario for every table.\n'+url+'\n'+' '.join('#'+t.upper() for t in tags)
                event=signed_note(signing_key(),int(time.time()),text,[['t',t] for t in tags])
                with lock:entry.update(nostr_event=event,nostr_landing=url);save()
            ws.send(json.dumps(['EVENT',event]))
            while True:
                msg=json.loads(ws.recv())
                if msg[:2]==['OK',event['id']]:
                    if not msg[2] and not msg[3].startswith('duplicate:'):raise RuntimeError('Relay declined publication')
                    break
            with lock:entry['nostr_post']='https://njump.me/'+event['id'];save()
    if entry.get('forum') and not entry.get('forum_landing'):
        url=landing(cfg['repo'],s,cfg['wallet'],'forum')
        ref=entry['forum']
        posts=api(BASE+'/api/threads/'+ref['thread_id'])['posts']
        body=next(p['body'] for p in posts if p['id']==ref['post_id'])
        if url not in body:
            if s['url'] not in body:return
            api(BASE+'/api/posts/'+ref['post_id']+'/edit',{'body':body.replace(s['url'],url)},identity('forum')['api_key'])
        with lock:entry['forum_landing']=url;save()
    if time.time()-entry.get('paths_checked',0)>3600:
        rows=gh('repos/'+cfg['repo']+'/traffic/popular/paths')
        with lock:
            for source in ('forum','nostr'):
                path=entry.get(source+'_landing','').removeprefix('https://github.com')
                match=next((r for r in rows if r['path']==path),None)
                entry[source+'_views']=match['count'] if match else None
            entry['paths_checked']=time.time();save()
