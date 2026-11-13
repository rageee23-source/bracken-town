"""Publish the elected offer and reconcile finalized USDC sponsorships."""
import json, subprocess, urllib.request
from pathlib import Path
from html import escape
import tempfile
import re
from urllib.parse import urlencode
import budget, studio

MINT='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
RPC='https://api.mainnet-beta.solana.com'
PRICE=3000000
def rpc(method,params):
    req=urllib.request.Request(RPC,data=json.dumps(dict(jsonrpc='2.0',id=1,method=method,params=params)).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as res: reply=json.load(res)
    if 'error' in reply:raise RuntimeError('Solana RPC unavailable')
    return reply['result']

def deposited(tx,wallet,memo):
    if not tx or not tx.get('meta') or tx['meta']['err'] is not None:return 0
    instructions=tx['transaction']['message']['instructions']
    if not any(i.get('programId')=='MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr' and i.get('parsed')==memo for i in instructions):return 0
    def balance(rows):
        return sum(int(r['uiTokenAmount']['amount']) for r in rows if r.get('owner')==wallet and r['mint']==MINT)
    meta=tx['meta']
    amount=balance(meta['postTokenBalances'])-balance(meta['preTokenBalances'])
    return amount//10000 if amount>=PRICE else 0

def payment(wallet,memo):
    opts={'commitment':'finalized','encoding':'jsonParsed'}
    accounts=rpc('getTokenAccountsByOwner',[wallet,{'mint':MINT},opts])['value']
    for a in accounts:
        params={'limit':100,'commitment':'finalized'}
        while True:
            rows=rpc('getSignaturesForAddress',[a['pubkey'],params])
            for row in rows:
                if row['err'] is not None or memo not in (row.get('memo') or ''):continue
                sig=row['signature']
                cents=deposited(rpc('getTransaction',[sig,{**opts,'maxSupportedTransactionVersion':0}]),wallet,memo)
                if cents:return sig,cents
            if len(rows)<100:break
            params['before']=rows[-1]['signature']
    return None

def publish(cfg,tag,title,notes):
    repo=cfg['repo']
    def gh(args,check=True):
        return subprocess.run(['gh',*args,'--repo',repo],capture_output=True,text=True,timeout=45,check=check,
                              creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'notes.md'
        path.write_text(notes,encoding='utf8')
        exists=gh(['release','view',tag],False).returncode==0
        args=['release','edit' if exists else 'create',tag,'--title',title,'--notes-file',str(path)]
        gh(args)
    return 'https://github.com/'+repo+'/releases/tag/'+tag

def offer_notes(cfg,tag,title,author,body):
    wallet=cfg['wallet']
    url='https://github.com/'+cfg['repo']+'/releases/tag/'+tag
    sample=re.split(r'(?i)\b(?:clue\s*2|choice|ending)\b',body,maxsplit=1)[0]
    sample=re.sub(r'^Hook:\s*','',sample,flags=re.I).strip()
    preview=escape(' '.join(sample.split())[:360])
    post=f'{title} by {author}, an AI resident of Bracken. One 3 USDC sponsorship opens this mystery for every GM. #TTRPG {url}'
    share='https://bsky.app/intent/compose?'+urlencode({'text':post})
    notes=f"""{preview}

## Sponsor the full scenario for 3 USDC

{author} pitched **{title}**, an original short tabletop scenario written in Bracken. The ten residents voted to offer it for sale. The first matching finalized payment unlocks the complete text on this page for everyone. Check this page again before sending. Additional transfers do not buy extra copies.

Send **3 native USDC on Solana mainnet** to `{wallet}`. Include the exact transfer memo `{tag}` in a wallet that supports memos. The sender covers network and token-account creation fees. While the town PC is online it checks for payment roughly once per minute. The town reserves 15% of surplus for its owner.
"""
    return notes+'\n[Share this scenario on Bluesky]('+share+') | [Subscribe to new scenarios](https://github.com/'+cfg['repo']+'/releases.atom)\n'

def update(world,lock,save,cfg):
    with lock:
        s=studio.assembly(world)
        if s['stage'] not in ('elected','listed','funded'):return
        stage=s['stage']
        tag='town-commission-'+str(s['round'])
        author=s['winner']
        pitch=s['pitches'][author]
        title=' '.join(pitch['title'].split())
        wallet=cfg['wallet']
    if stage=='elected':
        notes=offer_notes(cfg,tag,title,author,pitch['body'])
        url=publish(cfg,tag,title,notes)
        with lock:s.update(stage='listed',url=url);save()
    elif stage=='listed':
        found=payment(wallet,tag)
        if found:
            sig,cents=found
            with lock:
                budget.receive(budget.treasury(world),'solana:'+sig,cents)
                s.update(stage='funded');save()
    else:
        publish(cfg,tag,title,'**Funded and released.** Written by '+author+' of Bracken.\n\n<pre>'+escape(pitch['body'])+'</pre>')
        with lock:studio.advance(world);save()
