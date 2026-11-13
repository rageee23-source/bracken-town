"""Federated permission requests for individual, elected tabletop offers."""
import hashlib
import re
import secrets
import time
from urllib.parse import urlsplit
import requests
from town_accounts import VAULT, identity
from tabletop import landing

HOME='https://lemmy.sdf.org/api/v3'
BIO='Automated Bracken Town account. AI residents write tabletop scenarios. Project: https://github.com/rageee23-source/bracken-town'
DENY=re.compile(r'(?:no|ban(?:ned)?|prohibit(?:ed)?|not allowed|do not (?:allow|post))\s+(?:any\s+)?(?:ai|bots?|advertis|ads\b|self.promot|promotion)|(?:ai.generated|bots?|self.promotion).{0,30}(?:banned|not allowed)|zur freien|free (?:content|resources) only',re.I)
def eligible(url,row):
    u=urlsplit(url)
    return (u.scheme=='https' and re.fullmatch(r'/c/[\w-]+',u.path) and
            re.search(r'tabletop|ttrpg|role.?playing|solo.?rpg',row.get('name','')+' '+row.get('evidence',''),re.I)
            and not DENY.search(row.get('evidence','')))

def reply_state(text,ref):
    m=re.fullmatch(r'(yes|no)\s+'+re.escape(ref)+r'[.!]?',text.strip(),re.I)
    return {'yes':'approved','no':'declined'}[m[1].lower()] if m else 'clarification'

def call(method,path,token=None,**data):
    r=requests.request(method,HOME+path,params=data if method=='GET' else None,
                       json=data if method!='GET' else None,headers={'Authorization':'Bearer '+token} if token else {},timeout=15,allow_redirects=False)
    r.raise_for_status()
    return r.json()

def community(url,t):
    u=urlsplit(url)
    data=call('GET','/community',t,name=u.path.split('/')[-1]+'@'+u.hostname)
    c=data['community_view']['community']
    if c['actor_id'].rstrip('/')!=url.rstrip('/') or c.get('removed') or c.get('deleted'):raise ValueError('Community unavailable')
    return c,data['moderators']

def decide(record,messages,mods,own,records=()):
    actors={m['moderator']['actor_id'] for m in mods}
    latest=record.get('reply_id',0)
    for v in sorted(messages,key=lambda v:v['private_message']['id']):
        pm=v['private_message']
        if pm['id']<=latest or pm.get('deleted') or v['recipient']['actor_id']!=own or v['creator']['actor_id'] not in actors:continue
        content=pm['content'].strip()
        tagged=re.search(r'\b'+re.escape(record['ref'])+r'\b',content,re.I)
        direct=(pm['id']>record.get('sent_id',float('inf')) and v['creator']['actor_id']==record['moderator']
                and sum(r['moderator']==record['moderator'] for r in records)==1)
        if not tagged and not direct:continue
        if record['state']=='publishing' and pm['id']==record.get('reply_id'):continue
        decision=reply_state(content if tagged else content.rstrip('.!')+' '+record['ref'],record['ref'])
        record.update(state=decision,reply_id=pm['id'],
                      answered_by=v['creator']['actor_id'],answered_at=pm['published'],answer=pm['content'][:600])

def poll(world,lock,save,cfg):
    if not (VAULT/'lemmy.dpapi').exists():return
    with lock:
        board=world['marketing']
        book=board.setdefault('moderation',{'records':{}})
        if time.time()<book.get('next_check',0):return
        book['next_check']=time.time()+900
        s=world['studio'].copy()
        candidates=[(u,v) for u,v in board.get('venues',{}).items() if eligible(u,v)]
        save()
    cred=identity('lemmy')
    try:t=call('POST','/user/login',username_or_email=cred['username'],password=cred['password'])['jwt']
    except requests.HTTPError as e:
        code=e.response.json().get('error','login_unavailable')
        with lock:book['account']=code;save()
        return
    site=call('GET','/site',t)
    me=site['my_user']['local_user_view'];person=me['person']
    if not person.get('bot_account') or person.get('bio')!=BIO:
        call('PUT','/user/save_user_settings',t,bot_account=True,bio=BIO)
    with lock:book['account']='active';save()
    if s.get('stage')!='listed' or not s.get('social_copy'):return
    records=book['records']
    known={u for u,_ in candidates}
    candidates.extend((r['url'],{'activity':0}) for r in records.values() if r['round']==s['round'] and r['url'] not in known)
    # Read all incoming messages since the oldest outstanding request, newest first.
    messages=[]
    if records:
        cutoff=min((r.get('sent_id',0) for r in records.values() if r['round']==s['round']),default=0)
        page=1
        while True:
            batch=call('GET','/private_message/list',t,page=page,limit=50)['private_messages']
            messages.extend(batch)
            if len(batch)<50 or min(v['private_message']['id'] for v in batch)<=cutoff:break
            page+=1
    candidates.sort(key=lambda item:(item[0] not in [r['url'] for r in records.values()], 'selfpromo' not in item[0],-item[1].get('activity',0)))
    for url,row in candidates:
        source='lemmy-'+hashlib.sha256(url.encode()).hexdigest()[:12]
        key=str(s['round'])+'/'+source
        record=records.get(key)
        if not record and (time.time()<book.get('next_ask',0) or any(r['url']==url and r['state']=='declined' for r in records.values())):continue
        if record and record['state'] in ('posted','declined'):continue
        try:c,mods=community(url,t)
        except (requests.RequestException,ValueError):continue
        if not mods or DENY.search(c.get('description') or '') or c.get('posting_restricted_to_mods'):continue
        if not record:
            target=mods[0]['moderator']
            if target.get('deleted') or target.get('bot_account'):continue
            ref='BRK-'+secrets.token_hex(4)
            title=s['pitches'][s['winner']]['title']
            request=(f"Hello from Bracken Town, an automated tabletop project. May {s['winner']} publish one bot-labelled post in {url} about “{title}”? "
                     f"The post will identify its AI author, link to the scenario, and disclose optional 3 USDC sponsorship to unlock the complete adventure for everyone. "
                     f"The proposed pitch is: {s['social_copy']}\n\nFor this one post only, reply YES {ref} or NO {ref}. "
                     f"If conditions apply, please describe them with {ref}; the town will hold the post. No reply is needed to decline.")
            record=dict(url=url,source=source,round=s['round'],ref=ref,state='sending',moderator=target['actor_id'])
            with lock:records[key]=record;book['next_ask']=time.time()+86400;save()
            sent=call('POST','/private_message',t,recipient_id=target['id'],content=request)
            with lock:record.update(state='asked',sent_id=sent['private_message_view']['private_message']['id']);save()
            continue
        with lock:decide(record,messages,mods,person['actor_id'],records.values());save()
        if record['state']=='clarification' and not record.get('clarified'):
            target=next((m['moderator'] for m in mods if m['moderator']['actor_id']==record.get('answered_by')),None)
            if target:
                with lock:record['clarified']=True;save()
                ref=record['ref']
                call('POST','/private_message',t,recipient_id=target['id'],content=f'Thank you. I have held the post and saved your answer. If the original pitch is acceptable exactly as proposed, reply YES {ref}. Otherwise no action is needed.')
            continue
        if record['state']=='publishing':
            posts=call('GET','/post/list',t,community_id=c['id'],sort='New',limit=50)['posts']
            posted=next((p['post'] for p in posts if p['creator']['actor_id']==person['actor_id'] and p['post'].get('url')==record['landing']),None)
            if posted:
                with lock:record.update(state='posted',post=posted['ap_id']);save()
            continue
        if record['state']!='approved' or record['answered_by'] not in {m['moderator']['actor_id'] for m in mods}:continue
        link=landing(cfg['repo'],s,cfg['wallet'],source)
        with lock:
            if world['studio'].get('stage')!='listed' or world['studio']['round']!=s['round']:continue
            record.update(state='publishing',landing=link)
            board['campaigns'][str(s['round'])][source+'_landing']=link
            save()
        post=call('POST','/post',t,community_id=c['id'],name=s['pitches'][s['winner']]['title'],url=link,
                  body=s['social_copy']+'\n\nAI-written by '+s['winner']+' of Bracken Town. Optional 3 USDC sponsorship releases the full scenario for everyone.')
        with lock:record.update(state='posted',post=post['post_view']['post']['ap_id']);save()
