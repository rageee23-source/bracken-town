"""Town needs are reserves: 100 is satisfied, 0 is depleted."""
FACILITIES = {
    'Market': {'eat':'food stalls (2–3 coins per serving)','drink':'a water barrel'},
    'Bakery': {'eat':'paid baking shifts with a take-home loaf'},
    'Orchard': {'eat':'personal vegetable beds and emergency windfalls'},
    'Square': {'drink':'the public well'},
    'Riverbank': {'drink':'a spring-fed pump'},
    'Church': {'sleep':'quiet guest beds','socialize':'the chapel gathering'},
    'Town Hall': {'sleep':'the upstairs bunkroom','socialize':'the common room'},
}
NAMES = {'food':'Food','water':'Water','energy':'Energy','company':'Company'}
ACTIONS = {'eat':'food','drink':'water','sleep':'energy','socialize':'company'}
RATES = {'food':.087,'water':.13,'energy':.076,'company':.058}

def initialize(residents):
    for i,p in enumerate(residents):
        p.setdefault('needs',{k:44+(i*13+j*17)%43 for j,k in enumerate(NAMES)})
        p.setdefault('sleep_until',0)

def advance(residents,minute,step=4):
    for p in residents:
        sleeping=max(0,min(step,p['sleep_until']-minute))
        for key,rate in RATES.items():
            change=-rate*step
            if key=='energy':change=.24*sleeping-rate*(step-sleeping)
            p['needs'][key]=round(max(0,min(100,p['needs'][key]+change)),2)

def resolve(actor,people,minute,decision,world=None):
    dest=decision['destination']
    activity=decision['activity']
    reserves=actor['needs']
    # At critical reserves survival takes precedence, even over a distracted model.
    urgent=min(('water','food','energy'),key=lambda k:reserves[k])
    if reserves[urgent]<=20:
        activity={'water':'drink','food':'eat','energy':'sleep'}[urgent]
    elif reserves['company']<=20 and min(reserves[k] for k in ('food','energy','water'))>=35:
        activity='socialize'
    if world is not None:
        import economy
        if activity in economy.ECON_ACTIONS:return economy.act(actor,world,activity,dest)
    if activity=='pursue':return dest,decision['action'][:220],None
    awake=[p for p in people if p is not actor and p['sleep_until']<=minute]
    options=([p['place'] for p in awake] if activity=='socialize' else
             [place for place,offers in FACILITIES.items() if activity in offers])
    if not options:
        return 'Town Hall',actor['name']+' waited in the common room for company.',None
    if dest not in options:dest=actor['place'] if actor['place'] in options else options[0]
    name=actor['name']
    if activity=='sleep':
        actor['sleep_until']=minute+240
        text=f"{name} settled into {FACILITIES[dest]['sleep']} for four hours."
    elif activity=='socialize':
        partner=min((p for p in awake if p['place']==dest),key=lambda p:p['needs']['company'])
        for p in (actor,partner):p['needs']['company']=min(100,p['needs']['company']+35)
        text=f"{name} spent time with {partner['name']} at the {dest.lower()}."
    else:
        key=ACTIONS[activity];reserves[key]=min(100,reserves[key]+(52 if key=='water' else 43))
        verb='ate' if activity=='eat' else 'drank'
        text=f"{name} {verb} at {FACILITIES[dest][activity]}."
    return dest,text,activity
