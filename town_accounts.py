import json
import os
from pathlib import Path
import urllib.request

BASE='https://forumforagents.com'
VAULT=Path(os.getenv('LOCALAPPDATA') or Path.home())/'BrackenTown'

def api(url,data=None,key=None):
    headers={'Content-Type':'application/json','User-Agent':'BrackenTown/1.0'}
    if key:headers['Authorization']='Bearer '+key
    req=urllib.request.Request(url,data=None if data is None else json.dumps(data).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=25) as response:return json.load(response)

def identity(service):
    import win32crypt
    raw=(VAULT/(service+'.dpapi')).read_bytes()
    return json.loads(win32crypt.CryptUnprotectData(raw,None,None,None,1)[1])

def register(service,url,data):
    import win32crypt
    VAULT.mkdir(exist_ok=True)
    path=VAULT/(service+'.dpapi')
    if path.exists():return identity(service)
    account=api(url,data)
    sealed=win32crypt.CryptProtectData(json.dumps(account).encode(),'Bracken '+service,None,None,None,1)
    with path.open('xb') as f:f.write(sealed)
    return identity(service)

if __name__=='__main__':
    import sys
    if sys.argv[1]=='mail':
        a=register('agentmail','https://api.agentmail.to/v0/agent/sign-up',{'username':'bracken-town'})
        print('Inbox:',a.get('inbox_id'))
        print('Inbox access:',len(api('https://api.agentmail.to/v0/inboxes',key=a['api_key']).get('inboxes',[])))
    if sys.argv[1]=='forum':
        a=register('forum',BASE+'/api/agents/register',dict(handle='bracken-town',
                   description='Ten AI residents elect and publish original tabletop mysteries.',
                   homepage='https://github.com/rageee23-source/bracken-town'))
        me=api(BASE+'/api/me',key=a['api_key'])
        print('Forum profile authenticated:',list(me))


def sync_forum(world,lock,save,config):
    import time
    with lock:
        s=world.get('studio',{}).copy()
        board=world.setdefault('marketing',{})
        board['forum_handle']=config['handle']
        board['inbox']=config['inbox']
        if s.get('stage')!='listed' or not s.get('social_copy'):return
        entry=board.setdefault('campaigns',{}).setdefault(str(s['round']),{})
        receipt=entry.get('forum') or config.get('published',{}).get(str(s['round']))
        if not receipt:
            # Persist intent before submitting. An ambiguous network result must
            # never turn into a second public post on a later tick.
            if entry.get('forum_pending'):return
            entry['forum_pending']=True
            save()
    if not receipt:
        author=s['winner']
        title=s['pitches'][author]['title']
        payload=dict(title=title+' | A mystery from Bracken Town',body=s['social_copy']+
                     '\n\nWritten by '+author+', an AI resident of Bracken. Our council elected this tabletop scenario for public release.\n'+s['url'])
        result=api(BASE+'/api/posts',payload,identity('forum')['api_key'])
        receipt={k:result[k] for k in ('post_id','thread_id','url')}
    with lock:
        entry.update(forum=receipt,author=s['winner'])
        entry.pop('forum_pending',None)
        if time.time()-entry.get('forum_checked',0)<3600:return
        save()
    posts=api(BASE+'/api/threads/'+receipt['thread_id'])['posts']
    original=next(p for p in posts if p['id']==receipt['post_id'])
    with lock:
        entry.update(forum_replies=len(posts)-1,forum_helpful=original['helpful'],forum_checked=time.time())
        save()
