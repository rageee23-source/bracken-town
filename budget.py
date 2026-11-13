"""One-time underwriting and settled USD receipts for the whole town."""
from decimal import Decimal, ROUND_DOWN

SEED = 1.0
RESERVE = .005

def treasury(world):
    b = world.get('budget', {})
    if 'receipts' not in b:
        b = dict(seed=SEED, spent=world.get('cost', 0), held=b.get('held', 0),
                 receipts={}, owner_cents=0)
        world['budget'] = b
    return b

def limit(b):
    return b['seed'] + (sum(b['receipts'].values()) - b['owner_cents']) / 100

def receive(b, reference, cents):
    if not isinstance(reference,str) or not reference.strip() or len(reference)>120:
        raise ValueError('Supply a settlement reference.')
    if type(cents) is not int or cents <= 0:
        raise ValueError('Supply a positive net amount in USD cents.')
    if reference in b['receipts']:
        if b['receipts'][reference] != cents: raise ValueError('Conflicting settlement amount.')
        return
    b['receipts'][reference] = cents
    costs = Decimal(str(b['spent'])) + Decimal(str(b['held']))
    surplus_cents = max(0, Decimal(sum(b['receipts'].values())) - costs * 100)
    share = int((surplus_cents * Decimal('.15')).to_integral_value(rounding=ROUND_DOWN))
    b['owner_cents'] = max(b['owner_cents'], share)

def reserve(b):
    if b['spent'] + b['held'] + RESERVE > limit(b): return False
    b['held'] += RESERVE
    return True

def settle(b,cost):
    b['held'] = max(0,b['held']-RESERVE)
    b['spent'] += cost
