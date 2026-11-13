"""A resident publishes one pitch per elected offer and reads aggregate outcomes."""
import datetime
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request

def request(host,method,body=None,query=None,token=None):
    url=host+'/xrpc/'+method
    if query:url+='?'+urllib.parse.urlencode(query)
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers=headers)
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)

def publish(s,handle,password,created):
    host='https://bsky.social'
    session=request(host,'com.atproto.server.createSession',{'identifier':handle,'password':password})
    link=s['url']
    prefix=s['social_copy'][:175]+' — '+s['winner']+' of Bracken (AI). '
    text=prefix+link
    record={'$type':'app.bsky.feed.post','createdAt':created,'text':text,'facets':[{
        'index':{'byteStart':len(prefix.encode()),'byteEnd':len(text.encode())},
        'features':[{'$type':'app.bsky.richtext.facet#link','uri':link}]}]}
    # A stable record key makes a retry overwrite the same post after a lost response.
    result=request(host,'com.atproto.repo.putRecord',dict(repo=session['did'],collection='app.bsky.feed.post',
                   rkey='bracken-commission-'+str(s['round']),record=record),token=session['accessJwt'])
    return result['uri']

def traffic(repo):
    def gh(endpoint):
        out=subprocess.run(['gh','api','repos/'+repo+'/traffic/'+endpoint],capture_output=True,check=True,
                           timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return json.loads(out.stdout)
    views=gh('views')
    sources=gh('popular/referrers')
    return dict(reported_forum_referrals_14d=sum(v['count'] for v in sources if v['referrer']=='forumforagents.com'),repo_views_14d=views['count'],repo_visitors_14d=views['uniques'],
                reported_bsky_referrals_14d=sum(v['count'] for v in sources if v['referrer'] in ('bsky.app','go.bsky.app')))

def sync(world,lock,save,repo):
    with lock:
        s=world['studio'].copy() if 'studio' in world else {}
        board=world.setdefault('marketing',{})
        measurement_due=time.time()-board.get('checked',0)>3600
        handle=os.getenv('BRACKEN_BLUESKY_HANDLE')
        password=os.getenv('BRACKEN_BLUESKY_APP_PASSWORD')
        board['account']='Connected credentials' if handle and password else 'Awaiting town account'
    if measurement_due:
        stats=traffic(repo)
        with lock:board.update(stats,checked=time.time());save()
    if s.get('stage')!='listed' or not s.get('social_copy') or not (handle and password):return
    with lock:
        log=board.setdefault('campaigns',{})
        entry=log.setdefault(str(s['round']),{})
        if not entry.get('created'):
            entry['created']=datetime.datetime.now(datetime.timezone.utc).isoformat()
            save()
    if not entry.get('uri'):
        uri=publish(s,handle,password,entry['created'])
        with lock:entry.update(uri=uri,author=s['winner']);save()
    if time.time()-entry.get('checked',0)>3600:
        posts=request('https://public.api.bsky.app','app.bsky.feed.getPosts',query={'uris':entry['uri']})['posts']
        if posts:
            with lock:
                entry.update({k:posts[0].get(k,0) for k in ('likeCount','replyCount','repostCount')},checked=time.time())
                save()
