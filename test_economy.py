import unittest
from economy import act, setup
from needs import resolve

class EconomyTest(unittest.TestCase):
    def setUp(self):
        self.a,self.b=[dict(name=n,role=r,place='Square',needs=dict(food=70,water=70,energy=70,company=70)) for n,r in [('Alma','Botanist'),('Nell','Baker')]]
        self.world=dict(minutes=0,residents=[self.a,self.b])
        setup(self.world)
    def move(self,p,activity):return act(p,self.world,activity,'Square')
    def test_food_chain(self):
        w=self.world;a=self.a;b=self.b
        self.move(a,'plant');self.move(a,'harvest');self.assertEqual(a['pantry']['vegetables'],0)
        w['minutes']=160;self.move(a,'harvest');self.assertEqual(a['pantry']['vegetables'],5)
        self.move(a,'sell');self.assertEqual(a['coins'],10)
        self.move(b,'buy');self.assertEqual((b['coins'],a['coins'],a['pantry']['vegetables'],b['pantry']['vegetables']),(8,12,2,1))
        self.move(b,'work');self.assertEqual(w['economy']['treasury']+b['coins']+a['coins'],260)
        b['pantry']['bread']=0;b['needs']['food']=5
        resolve(b,w['residents'],160,{'activity':'work','destination':'Library'},w)
        self.assertEqual((b['needs']['food'],b['pantry']['vegetables']),(48,0))
        setup(w);self.assertEqual(b['coins'],12)
    def test_emergency_meal(self):
        self.a.update(coins=0,pantry={'bread':0,'vegetables':0})
        self.a['needs']['food']=0
        self.assertEqual(self.move(self.a,'eat')[0],'Orchard');self.assertEqual(self.a['needs']['food'],18)
if __name__=='__main__':unittest.main()
