import unittest
from unittest.mock import patch
import town, budget, economy
from needs import initialize

class Continuity(unittest.TestCase):
    def setUp(self):
        self.w = town.fresh()
        initialize(self.w['residents'])
        economy.setup(self.w)
        self.w.update(retry_at=0, failures=0)
        for change in (patch.object(town,'world',self.w), patch.object(town,'save'), patch.dict(town.os.environ, {'OPENAI_API_KEY':'test'})):
            change.start()
            self.addCleanup(change.stop)

    def test_cap_and_power(self):
        b=budget.treasury(self.w)
        b['spent']=30
        with patch.object(town,'choose',side_effect=AssertionError) as model:
            for _ in range(120): town.cycle()
            model.assert_not_called()
        self.assertEqual(self.w['cursor'],120)
        self.assertEqual(self.w['requests'],0)
        self.assertEqual(self.w['events'][-1]['source'],'Local')
        grid=self.w['economy']['grid']
        self.assertGreater(grid['owner'],0)
        self.assertEqual(grid['owner'],grid['exported'])
        self.assertEqual(grid['generated']+20,grid['stored']+grid['used']+grid['exported'])
        self.assertEqual(budget.treasury(self.w)['spent'],30)

    def test_outage_then_pause(self):
        with patch.object(town,'choose',side_effect=TimeoutError) as model:
            town.cycle()
            town.cycle()
            model.assert_called_once()
        self.assertEqual(self.w['cursor'],2)
        self.assertEqual(self.w['budget']['held'],budget.RESERVE)
        self.w['running']=False
        self.assertFalse(town.cycle())
        self.assertEqual(self.w['cursor'],2)
