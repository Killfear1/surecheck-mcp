#!/usr/bin/env python3
"""GTM Agent One local MCP server (stdio). No key or input is stored.

Reads SURECHECK_API_KEY (required) and SURECHECK_BASE_URL (default
https://surecheck-live-040.onrender.com). Exposes check_phone/check_email and
returns the API's structured result verbatim, including null/unknown states.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from urllib.parse import urlsplit

BASE = os.environ.get('SURECHECK_BASE_URL', 'https://surecheck-live-040.onrender.com').rstrip('/')
KEY = os.environ.get('SURECHECK_API_KEY', '')

TOOLS = [
    {'name': 'check_phone',
     'description': 'Validate a phone number with GTM Agent One numbering-plan metadata. Not live carrier, reachability, or ownership.',
     'inputSchema': {'type': 'object', 'properties': {
         'phone_number': {'type': 'string', 'description': 'Number, ideally E.164 (+...)', 'maxLength': 64},
         'country_code': {'type': 'string', 'description': 'Optional 2-letter region', 'maxLength': 2}},
         'required': ['phone_number'], 'additionalProperties': False}},
    {'name': 'check_email',
     'description': 'Validate an email with GTM Agent One syntax and DNS checks. Does not prove mailbox existence or delivery.',
     'inputSchema': {'type': 'object', 'properties': {
         'email': {'type': 'string', 'maxLength': 320}},
         'required': ['email'], 'additionalProperties': False}},
]

def note(msg):
    print(f'surecheck-mcp: {msg}', file=sys.stderr, flush=True)

def call_api(path, payload):
    if not KEY:
        return {'success': False, 'error': {'code': 'NO_API_KEY',
                'message': 'Set SURECHECK_API_KEY in the MCP server environment.'}}
    target = urlsplit(BASE)
    if target.scheme != 'https' or not target.hostname or target.username or target.password or target.query or target.fragment:
        return {'success': False, 'error': {'code': 'INVALID_BASE_URL',
                'message': 'SURECHECK_BASE_URL must be an HTTPS URL without credentials, query or fragment.'}}
    req = urllib.request.Request(BASE + path, method='POST',
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as r:
            result = json.loads(r.read())
            if not isinstance(result, dict):
                raise ValueError('Expected API object')
            return result
    except urllib.error.HTTPError as e:
        try:
            result = json.loads(e.read())
            if not isinstance(result, dict):
                raise ValueError('Expected API object')
            return result
        except Exception:
            return {'success': False, 'error': {'code': 'HTTP_' + str(e.code), 'message': 'API error.'}}
    except Exception:
        return {'success': False, 'error': {'code': 'UNREACHABLE', 'message': 'API unreachable. Free host may be waking; retry shortly.'}}

def text_result(obj):
    return {'content': [{'type': 'text', 'text': json.dumps(obj, indent=2)}],
            'isError': not obj.get('success', False)}

def rpc_error(mid, code, message):
    return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': code, 'message': message}}

def validate_args(name, args):
    schema = next(t['inputSchema'] for t in TOOLS if t['name'] == name)
    if not isinstance(args, dict):
        return False
    if any(k not in schema['properties'] for k in args):
        return False
    if any(k not in args for k in schema['required']):
        return False
    for key, value in args.items():
        if not isinstance(value, str) or not value.strip() or len(value) > schema['properties'][key]['maxLength']:
            return False
    if 'country_code' in args and (len(args['country_code']) != 2 or not args['country_code'].isascii() or not args['country_code'].isalpha()):
        return False
    return True

def handle(msg):
    if not isinstance(msg, dict):
        return rpc_error(None, -32600, 'Invalid request')
    mid = msg.get('id')
    if msg.get('jsonrpc') != '2.0' or not isinstance(msg.get('method'), str) or ('id' in msg and (isinstance(mid, (dict, list, bool)) or mid is None)):
        return rpc_error(None, -32600, 'Invalid request')
    # Valid notifications never produce a response or consume a check credit.
    if 'id' not in msg:
        return None
    method = msg['method']
    params = msg.get('params', {})
    if not isinstance(params, dict):
        return rpc_error(mid, -32602, 'Invalid params')
    if method == 'initialize':
        requested = params.get('protocolVersion')
        return {'jsonrpc': '2.0', 'id': mid, 'result': {
            'protocolVersion': requested if requested in ('2024-11-05', '2025-03-26', '2025-06-18') else '2024-11-05',
            'capabilities': {'tools': {}},
            'serverInfo': {'name': 'surecheck', 'version': '0.1.1'}}}
    if method == 'ping':
        return {'jsonrpc': '2.0', 'id': mid, 'result': {}}
    if method == 'tools/list':
        return {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': TOOLS}}
    if method == 'tools/call':
        name = params.get('name')
        if name not in ('check_phone', 'check_email'):
            return rpc_error(mid, -32602, 'Unknown tool')
        args = params.get('arguments', {})
        if not validate_args(name, args):
            return rpc_error(mid, -32602, 'Invalid tool arguments')
        path = '/api/v1/phone' if name == 'check_phone' else '/api/v1/email'
        return {'jsonrpc': '2.0', 'id': mid, 'result': text_result(call_api(path, args))}
    return rpc_error(mid, -32601, 'Method not found')

def main():
    if not KEY:
        note('SURECHECK_API_KEY is not set; tool calls will fail until configured.')
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            print(json.dumps(rpc_error(None, -32700, 'Parse error')), flush=True)
            continue
        out = handle(msg)
        if out is not None:
            print(json.dumps(out), flush=True)

if __name__ == '__main__':
    main()
