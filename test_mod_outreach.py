import unittest
from mod_outreach import decide, eligible

class ModeratorTest(unittest.TestCase):
    def test_scoped_verified_answers(self):
        r=dict(ref='BRK-aaaa',state='asked',moderator='mod',sent_id=11)
        mods=[{'moderator':{'actor_id':'mod'}}]
        def answer(n,text,actor='mod',recipient='town'):
            v=dict(private_message=dict(id=n,content=text,published='now'),recipient={'actor_id':recipient},creator={'actor_id':actor})
            decide(r,[v],mods,'town',[r])
        answer(12,'yes BRK-aaaa','other')
        answer(13,'yes BRK-aaaa',recipient='other')
        self.assertEqual(r['state'],'asked')
        answer(14,'yes, but only free material BRK-aaaa')
        self.assertEqual(r['state'],'clarification')
        answer(15,'YES')
        self.assertEqual(r['state'],'approved')
        answer(16,'NO BRK-aaaa')
        self.assertEqual(r['state'],'declined')
        answer(15,'YES')
        self.assertEqual(r['state'],'declined')

    def test_exclusion(self):
        self.assertFalse(eligible('https://example.com/c/ttrpg',dict(name='TTRPG',evidence='No AI generated adventures')))
