import unittest
import budget, council

class PolicyTest(unittest.TestCase):
    def test_settlement(self):
        w={'cost':.2,'budget':{'month':'2026-11','held':0}}
        b=budget.treasury(w)
        budget.receive(b,'sale',1020)
        budget.receive(b,'sale',1020)
        self.assertEqual(b['owner_cents'],150)
        self.assertAlmostEqual(budget.limit(b),9.70)
        with self.assertRaises(ValueError): budget.receive(b,'sale',300)
        self.assertIs(budget.treasury(w),b)

    def test_majority_and_tie(self):
        for count,target in [(6,12),(5,20)]:
            people=[{'name':str(i)} for i in range(10)]
            w={'economy':{'grid':{}},'residents':people,'minutes':0}
            for i,p in enumerate(people):
                council.vote(w,p,'yes' if i<count else 'no','Local')
                council.vote(w,p,'yes','Local')
            self.assertEqual(w['economy']['grid']['target'],target)
            self.assertEqual(len(w['hall']['history']),1)
