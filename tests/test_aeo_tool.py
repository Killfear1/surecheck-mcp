import unittest, surecheck_mcp as m
class T(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(m.validate_args('run_aeo_agent', {'url': 'https://acme.example'}))
        self.assertTrue(m.validate_args('run_aeo_agent', {'url': 'https://acme.example', 'extra_urls': ['https://acme.example/a']}))
    def test_invalid(self):
        for a in [{}, {'url': ''}, {'url': 'x'*301}, {'url': 'https://a.example', 'extra_urls': ['a','b','c']}, {'url': 'https://a.example', 'x': 'y'}, {'url': 5}]:
            self.assertFalse(m.validate_args('run_aeo_agent', a), a)
    def test_routes(self):
        seen = {}
        m.call_api = lambda path, payload, timeout=20: seen.update(p=path, t=timeout) or {'success': True}
        r = m.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'run_aeo_agent', 'arguments': {'url': 'https://a.example'}}})
        self.assertEqual(seen['p'], '/api/v1/agent/aeo'); self.assertIn('result', r)
unittest.main() if __name__ == '__main__' else None
