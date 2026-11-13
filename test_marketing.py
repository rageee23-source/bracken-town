import unittest
from unittest.mock import patch
import marketing
import studio

class ResidentMarketing(unittest.TestCase):
    def test_author_and_retry(self):
        s=dict(stage='listed',winner='Finn',round=1,url='https://example.org/1',
               pitches={'Finn':{'body':'A potter lost his recipe.'}})
        w={'studio':s}
        self.assertIsNone(studio.task(w,{'name':'Alma'}))
        studio.record(w,{'name':'Finn'},{'social_copy':'A potter’s clue.'},'OpenAI')
        with patch.object(marketing,'request',side_effect=[{'did':'did:plc:town','accessJwt':'test'},{'uri':'record'}]*2) as req:
            for _ in range(2):marketing.publish(s,'town','test','fixed')
            first=req.call_args_list[1].args[2]
            self.assertEqual(first,req.call_args_list[3].args[2])
            record=first['record']; span=record['facets'][0]['index']
            self.assertEqual(record['text'].encode()[span['byteStart']:span['byteEnd']].decode(),s['url'])
