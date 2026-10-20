import unittest
from unittest.mock import patch
import surecheck_mcp as m

OK = {'csv': 'domain\nexample.com\n', 'offer': 'We check lead emails.', 'sender': 'Sam'}

class BusinessToolTests(unittest.TestCase):
    def call(self, args):
        return m.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'run_business_agent', 'arguments': args}})

    def test_valid_args(self):
        self.assertTrue(m.validate_args('run_business_agent', OK))
        self.assertTrue(m.validate_args('run_business_agent', dict(OK, agents=['validator', 'page_builder'], page_points=['One', 'Two'], page_name='Acme', icp='plumbing')))

    def test_invalid_args(self):
        bad = [dict(OK, agents=['send_email']), dict(OK, agents='validator'), dict(OK, agents=[1]), dict(OK, agents=['validator'] * 8),
               dict(OK, page_points=['x'] * 6), dict(OK, page_points=['x' * 121]), dict(OK, page_points=['']), dict(OK, extra='x'),
               {'csv': 'domain\na.com\n', 'offer': 'x'}, dict(OK, csv='x' * 20001), dict(OK, sender='')]
        for a in bad:
            with self.subTest(a=str(a)[:60]):
                self.assertFalse(m.validate_args('run_business_agent', a))
                self.assertEqual(self.call(a)['error']['code'], -32602)

    def test_posts_to_business_endpoint_with_long_timeout(self):
        with patch.object(m, 'call_api', return_value={'success': True, 'data': {}}) as c:
            r = self.call(OK)['result']
        c.assert_called_once_with('/api/v1/agent/business', OK, timeout=120)
        self.assertFalse(r['isError'])

    def test_phone_and_email_still_use_default_timeout(self):
        with patch.object(m, 'call_api', return_value={'success': True}) as c:
            m.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'check_email', 'arguments': {'email': 'a@example.com'}}})
        c.assert_called_once_with('/api/v1/email', {'email': 'a@example.com'})

    def test_notification_costs_nothing(self):
        with patch.object(m, 'call_api') as c:
            self.assertIsNone(m.handle({'jsonrpc': '2.0', 'method': 'tools/call', 'params': {'name': 'run_business_agent', 'arguments': OK}}))
        c.assert_not_called()

if __name__ == '__main__':
    unittest.main()
