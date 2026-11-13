"""All balances are fictional whole coins. A listing holds physical food until bought."""
JOBS = {
    'Botanist':('Orchard','tended the communal seedlings'),
    'Clockmaker':('Workshop','serviced the town clock'),
    'Baker':('Bakery','staffed the communal oven'),
    'Ferryman':('Riverbank','worked a ferry crossing'),
    'Archivist':('Library','catalogued town records'),
    'Carpenter':('Workshop','repaired the market stalls'),
    'Musician':('Town Hall','played a public concert'),
    'Potter':('Workshop','made vessels for the well'),
    'Cartographer':('Library','updated the town maps'),
    'Apprentice':('Market','unloaded a delivery'),
}
COOP='Town co-op'
GOODS={'bread','vegetables'}
ECON_ACTIONS=['generate','work','plant','harvest','sell','buy','eat']
def setup(world):
    if 'economy' not in world:
        world['economy']={'treasury':240,'listings':[
            {'seller':COOP,'item':'bread','quantity':16,'price':3},
            {'seller':COOP,'item':'vegetables','quantity':12,'price':2}],
            'ledger':[]}
    world['economy'].setdefault('grid',dict(stored=20,generated=0,used=0,unserved=0,exported=0,owner=0))
    for p in world['residents']:
        p.setdefault('coins',10)
        p.setdefault('pantry',{'bread':1,'vegetables':0})
        p.setdefault('crop_ready',None)
        p['job_place']=JOBS[p['role']][0]
def log(e,minute,text):
    e['ledger']=(e['ledger']+[{'minute':minute,'text':text}])[-60:]
def trade(p,world):
    e=world['economy']
    offers=[o for o in e['listings'] if o['quantity']>0 and o['seller']!=p['name'] and o['price']<=p['coins']]
    if not offers:return None
    offer=min(offers,key=lambda o:(o['price'],o['seller']==COOP))
    price=offer['price'];seller=offer['seller']
    if seller==COOP:e['treasury']+=price
    else:next(r for r in world['residents'] if r['name']==seller)['coins']+=price
    p['coins']-=price;p['pantry'][offer['item']]+=1;offer['quantity']-=1
    if not offer['quantity']:e['listings'].remove(offer)
    log(e,world['minutes'],f"{p['name']} paid {seller} {price} coins for {offer['item']}.")
    return offer['item']
def act(p,world,activity,dest):
    e=world['economy'];minute=world['minutes'];name=p['name'];bag=p['pantry']
    if activity=='generate':
        g=e['grid'];g['generated']+=18;g['stored']+=18
        wage=min(4,e['treasury']);e['treasury']-=wage;p['coins']+=wage
        text=f'{name} ran the river generator for 18 power units and earned {wage} coins.'
        log(e,minute,text);return 'Riverbank',text,activity
    if activity=='work':
        dest,task=JOBS[p['role']]
        if e['treasury']<4:return dest,f'{name} found no funded shift today.',activity
        e['treasury']-=4;p['coins']+=4
        if p['role']=='Baker':bag['bread']+=1
        text=f'{name} {task} for 4 coins.'+(' Took home a loaf.' if p['role']=='Baker' else '')
        log(e,minute,text);return dest,text,activity
    if activity=='plant':
        dest='Orchard'
        if p['crop_ready'] is not None:return dest,f'{name} checked an already planted bed.',activity
        p['crop_ready']=minute+160
        return dest,f'{name} planted vegetables in a personal allotment.',activity
    if activity=='harvest':
        dest='Orchard'
        if p['crop_ready'] is None or minute<p['crop_ready']:return dest,f'{name} inspected the plot; nothing was ready to harvest.',activity
        p['crop_ready']=None;bag['vegetables']+=5
        return dest,f'{name} harvested five portions of vegetables.',activity
    if activity=='sell':
        item=max(sorted(GOODS),key=bag.get)
        if not bag[item]:return 'Market',f'{name} had no food to list.',activity
        qty=min(3,bag[item]);bag[item]-=qty;price=2 if item=='vegetables' else 3
        offer=next((o for o in e['listings'] if o['seller']==name and o['item']==item),None)
        if offer:offer['quantity']+=qty
        else:e['listings'].append(dict(seller=name,item=item,quantity=qty,price=price))
        text=f'{name} listed {qty} portions of {item} at {price} coins each.'
        log(e,minute,text);return 'Market',text,activity
    if activity=='buy':
        item=trade(p,world)
        return 'Market',f'{name} bought {item} for the pantry.' if item else f'{name} found no affordable food on sale.',activity
    if activity=='eat':
        item=next((k for k in ('bread','vegetables') if bag[k]),None)
        if item is None:
            dest='Market';item=trade(p,world)
        if item:
            bag[item]-=1;p['needs']['food']=min(100,p['needs']['food']+43)
            return dest,f'{name} ate a portion of {item}.',activity
        p['needs']['food']=min(100,p['needs']['food']+18)
        return 'Orchard',f'{name} gathered windfalls for a small meal.',activity
    raise ValueError('Unknown economic activity')
def grid_tick(world):
    """Four simulated minutes consume one unit. Sell only above the reserve."""
    e=world['economy'];g=e.setdefault('grid',{'stored':20,'generated':0,'used':0,'unserved':0,'exported':0,'owner':0})
    if g['stored']:
        g['stored']-=1;g['used']+=1
    else:g['unserved']+=1
    surplus=max(0,g['stored']-g.get('target',20))
    if surplus:
        g['stored']-=surplus;g['exported']+=surplus
        # An external fictional grid buyer pays five coins per surplus unit.
        e['treasury']+=4*surplus;g['owner']+=surplus
        log(e,world['minutes'],f'Exported {surplus} power units: {4*surplus} coins to town, {surplus} to the owner.')
