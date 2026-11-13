"""Residents vote once per assembly on a binding power reserve target."""
def session(world):
    grid = world['economy']['grid']
    grid.setdefault('target', 20)
    hall = world.setdefault('hall', {'history': [], 'next': 0, 'motion': None})
    if hall['motion'] is None and world['minutes'] >= hall['next']:
        target = 12 if grid['target'] == 20 else 20
        hall['motion'] = {'text': f'Set the river power reserve to {target} units before selling surplus.',
                          'target': target, 'ballots': {}}
    return hall['motion']

def vote(world, resident, ballot, source):
    motion = session(world)
    if not motion or resident['name'] in motion['ballots']: return
    if ballot not in ('yes','no'):
        return
    motion['ballots'][resident['name']] = {'vote': ballot, 'source': source}
    if len(motion['ballots']) == len(world['residents']):
        passed = sum(v['vote']=='yes' for v in motion['ballots'].values()) > len(world['residents'])//2
        motion.update(passed=passed,minute=world['minutes'])
        if passed: world['economy']['grid']['target'] = motion['target']
        hall=world['hall']
        hall['history']=(hall['history']+[motion])[-30:]
        hall.update(motion=None,next=world['minutes']+1440)
