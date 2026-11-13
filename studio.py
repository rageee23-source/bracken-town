"""Town hall chooses one ready-to-play scenario for a public-release commission."""
from collections import Counter
import hashlib

def assembly(world):
    return world.setdefault('studio',dict(round=1,pitches={},votes={},stage='pitch'))

def task(world,actor):
    s=assembly(world)
    name=actor['name']
    if s['stage']=='pitch' and name not in s['pitches']:
        return ('pitch','Present a distinctive short tabletop mystery related to your trade. Return a title in pitch and a complete playable scenario in manuscript (100-160 words): hook, three discoverable clues, a choice and two endings. Write original fiction.')
    if s['stage']=='vote' and name not in s['votes']:
        options={k:v['title'] for k,v in s['pitches'].items()}
        return ('vote','Vote for one proposal to sell as a public-release commission. Return the exact author name in selection. Candidates: '+str(options))
    if s['stage']=='listed' and name==s['winner'] and not s.get('social_copy'):
        return ('promote','Write your own Bluesky pitch for game masters in social_copy, up to 175 characters. Use the hook from your scenario and mention the 3 USDC public unlock. No links. Scenario: '+s['pitches'][name]['body'])
    return None

def record(world,actor,decision,source):
    s=assembly(world)
    todo=task(world,actor)
    if not todo:return
    name=actor['name']
    if todo[0]=='promote':
        copy=decision.get('social_copy')
        if isinstance(copy,str) and copy.strip():s['social_copy']=' '.join(copy.split())[:175]
        return
    if todo[0]=='pitch':
        title=decision.get('pitch','')
        manuscript=decision.get('manuscript','')
        if not isinstance(title,str) or not isinstance(manuscript,str) or not (3<=len(title.strip())<=140 and 240<=len(manuscript.strip())<=3500):return
        s['pitches'][name]=dict(title=title.strip(),body=manuscript.strip(),source=source)
        if len(s['pitches'])>=3:s['stage']='vote'
    else:
        candidate=decision.get('selection')
        if source=='Local':
            candidate=max(s['pitches'],key=lambda n:hashlib.sha256((name+str(s['round'])+n).encode()).digest())
        if candidate not in s['pitches']:return
        s['votes'][name]=dict(candidate=candidate,source=source)
        if len(s['votes'])==len(world['residents']):
            counts=Counter(v['candidate'] for v in s['votes'].values())
            s['winner']=max(s['pitches'],key=lambda n:counts[n])
            s['stage']='elected'

def advance(world):
    s=assembly(world)
    world.setdefault('commissions',[]).append(dict(round=s['round'],winner=s['winner'],url=s['url'],title=s['pitches'][s['winner']]['title']))
    world['studio']=dict(round=s['round']+1,pitches={},votes={},stage='pitch')
