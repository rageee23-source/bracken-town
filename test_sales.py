import threading
import unittest
from unittest.mock import Mock, patch
import sales, studio

class SalesTest(unittest.TestCase):
    def setUp(self):
        self.w={'residents':[{'name':n} for n in 'ABCDEFGHIJ']}
        self.cfg={'wallet':'recipient','repo':'town/test'}
        self.lock=threading.RLock()

    def test_election_to_fulfillment(self):
        people=self.w['residents']
        for p in people[:3]:
            studio.record(self.w,p,dict(pitch='Pitch '+p['name'],manuscript='A clue. '*42),'OpenAI')
        for p in people:
            studio.record(self.w,p,dict(selection='B'),'OpenAI')
            studio.record(self.w,p,dict(selection='C'),'OpenAI')
        with patch.object(sales,'publish',return_value='https://example.org/offer') as publish, patch.object(sales,'payment',return_value=('sig',300)):
            for _ in range(3):sales.update(self.w,self.lock,Mock(),self.cfg)
        self.assertEqual(publish.call_count,2)
        self.assertEqual(self.w['budget']['owner_cents'],45)
        self.assertEqual(self.w['commissions'][0]['winner'],'B')
        self.assertEqual(self.w['studio']['round'],2)

    def test_payment(self):
        def bal(n):return dict(owner='recipient',mint=sales.MINT,uiTokenAmount={'amount':str(n)})
        tx={'transaction':{'message':{'instructions':[{'programId':'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr','parsed':'order'}]}},
            'meta':{'err':None,'preTokenBalances':[bal(2000000)],'postTokenBalances':[bal(5000000)]}}
        self.assertEqual(sales.deposited(tx,'recipient','order'),300)
        self.assertEqual(sales.deposited(tx,'recipient','other'),0)
        self.assertEqual(sales.deposited(tx,'other','order'),0)
        tx['meta']['postTokenBalances']=[bal(4999999)]
        self.assertEqual(sales.deposited(tx,'recipient','order'),0)
        tx['meta']['err']='failed'
        self.assertEqual(sales.deposited(tx,'recipient','order'),0)
