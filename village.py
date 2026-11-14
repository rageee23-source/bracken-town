"""Public village snapshot and a bounded, source-attributed play counter."""
import base64,datetime,json,re,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from tabletop import gh

def snapshot(w,places,book):
    def public(text):
        return not re.search(r'\b(?:owner|tax\w*|api|treasury|payroll|operator)\b|https?://',text,re.I)
    return dict(updated=datetime.datetime.now(datetime.timezone.utc).isoformat(),book=book,
        people=[dict(name=p['name'],role=p['role'],place=p['place'],goal=p['goal'] if public(p['goal']) else '',
                     x=places[p['place']][0],y=places[p['place']][1]) for p in w['residents']],
        events=[e['action'][:180] for e in w['events'][-30:] if public(e['action'])][-5:][::-1])

def upload(repo,path,value):
    endpoint='repos/'+repo+'/contents/docs/'+path
    import subprocess
    try:old=gh(endpoint)
    except subprocess.CalledProcessError as e:
        if '404' not in e.stderr:raise
        old={}
    data=dict(message='Update public village '+path,content=base64.b64encode(json.dumps(value,ensure_ascii=False).encode()).decode())
    if old:data['sha']=old['sha']
    gh(endpoint,'--method','PUT','--input','-',data=data)

def visitors(w,lock,save,cfg,places):
    v=w.setdefault('visitors',{})
    now=time.time()
    if now<v.get('check',0):return
    v['check']=now+300
    repo=cfg['repo'];issue=cfg['guestbook']
    comments=gh(f'repos/{repo}/issues/{issue}/comments?per_page=100&sort=created&direction=desc')
    handled=v.setdefault('handled',[])
    if not v.get('letter'):
        for c in sorted(comments,key=lambda c:c['id']):
            if c['id'] in handled or c['user']['login']==repo.split('/')[0]:continue
            who=next((p['name'] for p in w['residents'] if re.search(r'\b'+p['name']+r'\b',c['body'],re.I)),'Bea')
            with lock:v['letter']=dict(id=c['id'],name=who,text=c['body'][:500]);save()
            break
    letter=v.get('letter') or {}
    if letter.get('reply'):
        mark='<!-- bracken-letter-'+str(letter['id'])+' -->'
        if not any(c['body'].endswith(mark) and c['user']['login']==repo.split('/')[0] for c in comments):
            gh(f'repos/{repo}/issues/{issue}/comments','--method','POST','--input','-',data={'body':'**'+letter['name']+' of Bracken**\n\n'+letter['reply']+'\n\n'+mark})
        with lock:handled.append(letter['id']);v.pop('letter',None);save()
    if now>v.get('snapshot',0)+1800:
        with lock:data=snapshot(w,places,'https://github.com/'+repo+'/issues/'+str(issue))
        upload(repo,'village.json',data)
        with lock:v['snapshot']=now;save()

def metrics(w,lock,save):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            allowed='/bracken-town'
            if self.path!='/play' or self.headers.get('Origin')!='https://rageee23-source.github.io':
                self.send_error(403);return
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<400:raise ValueError()
                d=json.loads(self.rfile.read(n))
                with lock:
                    c=w['marketing']['campaigns'][str(int(d['round']))]
                    source=d['source'];sid=d['session'];step=d['step']
                    if source!='direct' and not c.get(source+'_landing'):raise ValueError()
                    if not re.fullmatch('[a-f0-9]{32}',sid) or step not in ('start','finish'):raise ValueError()
                    seen=w.setdefault('play_sessions',{});now=time.time()
                    if len(seen)>10000:raise ValueError()
                    key=source+'-'+sid
                    prior=seen.get(key)
                    if step=='start' and not prior or step=='finish' and prior and prior[0]=='start':
                        counts=c.setdefault('plays',{}).setdefault(source,{'start':0,'finish':0})
                        counts[step]+=1;seen[key]=[step,now]
                        for k in [k for k,v in seen.items() if now-v[1]>86400]:seen.pop(k)
                        save()
                self.send_response(204);self.send_header('Access-Control-Allow-Origin','https://rageee23-source.github.io');self.end_headers()
            except (ValueError,KeyError,TypeError):self.send_error(400)
    ThreadingHTTPServer(('127.0.0.1',8799),Handler).serve_forever()
