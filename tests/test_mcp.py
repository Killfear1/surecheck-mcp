import io
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import surecheck_mcp as m

class ProtocolTests(unittest.TestCase):
    def request(self, method, params=None, mid=1):
        msg = {'jsonrpc': '2.0', 'id': mid, 'method': method}
        if params is not None:
            msg['params'] = params
        return m.handle(msg)

    def test_initialize_versions(self):
        for version in ('2024-11-05', '2025-03-26', '2025-06-18'):
            with self.subTest(version=version):
                r = self.request('initialize', {'protocolVersion': version})
                self.assertEqual(r['result']['protocolVersion'], version)

    def test_initialize_fallback(self):
        self.assertEqual(self.request('initialize', {'protocolVersion': 'future'})['result']['protocolVersion'], '2024-11-05')

    def test_ping_zero_id(self):
        self.assertEqual(self.request('ping', mid=0)['id'], 0)

    def test_tools(self):
        self.assertEqual([x['name'] for x in self.request('tools/list')['result']['tools']], ['check_phone', 'check_email', 'run_business_agent', 'run_aeo_agent'])

    def test_invalid_requests(self):
        for msg in ([], None, 1, '', {'method': 'ping'}, {'jsonrpc': '2.0', 'method': 4}, {'jsonrpc': '2.0', 'method': 'ping', 'id': []}, {'jsonrpc': '2.0', 'method': 'ping', 'id': True}):
            with self.subTest(msg=msg):
                self.assertEqual(m.handle(msg)['error']['code'], -32600)

    def test_invalid_params(self):
        for params in ([], 'x', 7):
            self.assertEqual(self.request('initialize', params)['error']['code'], -32602)

    def test_notifications_silent_no_charge(self):
        with patch.object(m, 'call_api') as call:
            self.assertIsNone(m.handle({'jsonrpc': '2.0', 'method': 'tools/call', 'params': {'name': 'check_email', 'arguments': {'email': 'a@example.com'}}}))
            call.assert_not_called()

    def test_unknown_method(self):
        self.assertEqual(self.request('missing')['error']['code'], -32601)

    def test_unknown_tool(self):
        self.assertEqual(self.request('tools/call', {'name': 'missing'})['error']['code'], -32602)

    def test_bad_arguments_do_not_call_api(self):
        bad = [None, [], 'x', {}, {'email': 3}, {'email': ''}, {'email': ' '}, {'email': 'x'*321}, {'email': 'a@example.com', 'extra': 'x'}]
        with patch.object(m, 'call_api') as call:
            for args in bad:
                with self.subTest(args=args):
                    self.assertEqual(self.request('tools/call', {'name': 'check_email', 'arguments': args})['error']['code'], -32602)
            call.assert_not_called()

    def test_country_code(self):
        for value in ('USA', '1A', 'éé', '', 'A'):
            self.assertFalse(m.validate_args('check_phone', {'phone_number': '+12025550123', 'country_code': value}))
        self.assertTrue(m.validate_args('check_phone', {'phone_number': '+12025550123', 'country_code': 'us'}))

    def test_phone_forwarding_and_unknown_preserved(self):
        payload = {'success': True, 'carrier': None, 'valid': False}
        with patch.object(m, 'call_api', return_value=payload) as call:
            args = {'phone_number': '+12025550123', 'country_code': 'US'}
            result = self.request('tools/call', {'name': 'check_phone', 'arguments': args})['result']
            call.assert_called_once_with('/api/v1/phone', args)
            self.assertEqual(json.loads(result['content'][0]['text']), payload)
            self.assertFalse(result['isError'])

    def test_email_forwarding(self):
        with patch.object(m, 'call_api', return_value={'success': False}) as call:
            r = self.request('tools/call', {'name': 'check_email', 'arguments': {'email': 'a@example.com'}})
            call.assert_called_once_with('/api/v1/email', {'email': 'a@example.com'})
            self.assertTrue(r['result']['isError'])

    def test_subprocess_survives_bad_input(self):
        env = dict(os.environ, SURECHECK_API_KEY='')
        p = subprocess.run([sys.executable, 'surecheck_mcp.py'], input='oops\n[]\n'+json.dumps({'jsonrpc':'2.0','id':1,'method':'ping'})+'\n', text=True, capture_output=True, env=env)
        self.assertEqual(p.returncode, 0)
        rows = [json.loads(x) for x in p.stdout.splitlines()]
        self.assertEqual([r.get('error', {}).get('code') for r in rows], [-32700, -32600, None])

class ApiTests(unittest.TestCase):
    def test_missing_key(self):
        with patch.object(m, 'KEY', ''):
            self.assertEqual(m.call_api('/x', {})['error']['code'], 'NO_API_KEY')

    def test_unsafe_base(self):
        for base in ('http://example.com', 'https://user:pass@example.com', 'https://example.com?secret=x', 'https://example.com#x', 'file:///tmp/a'):
            with self.subTest(base=base), patch.object(m, 'KEY', 'synthetic'), patch.object(m, 'BASE', base), patch.object(m.urllib.request, 'build_opener') as opener:
                self.assertEqual(m.call_api('/x', {})['error']['code'], 'INVALID_BASE_URL')
                opener.assert_not_called()

    def test_response_object(self):
        with patch.object(m, 'KEY', 'synthetic'), patch.object(m.urllib.request, 'build_opener') as build:
            response = build.return_value.open.return_value.__enter__.return_value
            response.read.return_value = b'{"success":true,"carrier":null}'
            self.assertEqual(m.call_api('/x', {}), {'success': True, 'carrier': None})

    def test_redirects_are_disabled(self):
        with patch.object(m, 'KEY', 'synthetic'), patch.object(m.urllib.request, 'build_opener') as build:
            build.return_value.open.return_value.__enter__.return_value.read.return_value = b'{"success":true}'
            m.call_api('/x', {})
            handler = build.call_args.args[0]()
            self.assertIsNone(handler.redirect_request(None, None, 302, 'redirect', {}, 'https://other.example'))

    def test_phone_limits(self):
        for value in ('', ' ', 'x' * 65, 42):
            self.assertFalse(m.validate_args('check_phone', {'phone_number': value}))

    def test_response_list_handled(self):
        with patch.object(m, 'KEY', 'synthetic'), patch.object(m.urllib.request, 'build_opener') as build:
            build.return_value.open.return_value.__enter__.return_value.read.return_value = b'[]'
            self.assertEqual(m.call_api('/x', {})['error']['code'], 'UNREACHABLE')

    def test_network_failure(self):
        with patch.object(m, 'KEY', 'synthetic'), patch.object(m.urllib.request, 'build_opener') as build:
            build.return_value.open.side_effect = OSError('offline')
            self.assertEqual(m.call_api('/x', {})['error']['code'], 'UNREACHABLE')

    def test_http_json_error(self):
        with patch.object(m, 'KEY', 'synthetic'), patch.object(m.urllib.request, 'build_opener') as build:
            build.return_value.open.side_effect = HTTPError('https://example.com', 401, 'no', {}, io.BytesIO(b'{"success":false,"error":{"code":"BAD_KEY"}}'))
            self.assertEqual(m.call_api('/x', {})['error']['code'], 'BAD_KEY')

    def test_http_non_object(self):
        with patch.object(m, 'KEY', 'synthetic'), patch.object(m.urllib.request, 'build_opener') as build:
            build.return_value.open.side_effect = HTTPError('https://example.com', 500, 'no', {}, io.BytesIO(b'[]'))
            self.assertEqual(m.call_api('/x', {})['error']['code'], 'HTTP_500')

if __name__ == '__main__':
    unittest.main()
