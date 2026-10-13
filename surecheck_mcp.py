#!/usr/bin/env python3
"""SureCheck local MCP server (stdio). No key or input is stored.

Reads SURECHECK_API_KEY (required) and SURECHECK_BASE_URL (default
https://surecheck-live-040.onrender.com). Exposes check_phone/check_email and
returns the API's structured result verbatim, including null/unknown states.
"""
import json
import os
import sys
import urllib.request
import urllib.error

BASE = os.environ.get('SURECHECK_BASE_URL', 'https://surecheck-live-040.onrender.com').rstrip('/')
KEY = os.environ.get('SURECHECK_API_KEY', '')

TOOLS = [
    {'name': 'check_phone',
     'description': 'Validate a phone number via SureCheck numbering-plan metadata. Not live carrier, reachability, or ownership.',
     'inputSchema': {'type': 'object', 'properties': {
         'phone_number': {'type': 'string', 'description': 'Number, ideally E.164 (+...)', 'maxLength': 64},
         'country_code': {'type': 'string', 'description': 'Optional 2-letter region', 'maxLength': 2}},
         'required': ['phone_number'], 'additionalProperties': False}},
    {'name': 'check_email',
     'description': 'Validate an email via SureCheck syntax and DNS. Does not prove mailbox existence or delivery.',
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
    req = urllib.request.Request(BASE + path, method='POST',
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {'success': False, 'error': {'code': 'HTTP_' + str(e.code), 'message': 'API error.'}}
    except Exception:
        return {'success': False, 'error': {'code': 'UNREACHABLE', 'message': 'API unreachable. Free host may be waking; retry shortly.'}}

def text_result(obj):
    return {'content': [{'type': 'text', 'text': json.dumps(obj, indent=2)}],
            'isError': not obj.get('success', False)}

def handle(msg):
    method = msg.get('method')
    mid = msg.get('id')
    if method == 'initialize':
        return {'jsonrpc': '2.0', 'id': mid, 'result': {
            'protocolVersion': (msg.get('params', {}).get('protocolVersion') if msg.get('params', {}).get('protocolVersion') in ('2024-11-05', '2025-03-26', '2025-06-18') else '2024-11-05'),
            'capabilities': {'tools': {}},
            'serverInfo': {'name': 'surecheck', 'version': '0.1.1'}}}
    if method == 'notifications/initialized' or method == 'ping':
        return {'jsonrpc': '2.0', 'id': mid, 'result': {}} if mid is not None else None
    if method == 'tools/list':
        return {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': TOOLS}}
    if method == 'tools/call':
        p = msg.get('params', {})
        name, args = p.get('name'), p.get('arguments') or {}
        if name == 'check_phone':
            body = {'phone_number': args.get('phone_number', '')}
            if args.get('country_code'):
                body['country_code'] = args['country_code']
            return {'jsonrpc': '2.0', 'id': mid, 'result': text_result(call_api('/api/v1/phone', body))}
        if name == 'check_email':
            return {'jsonrpc': '2.0', 'id': mid, 'result': text_result(call_api('/api/v1/email', {'email': args.get('email', '')}))}
        return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': 'Unknown tool'}}
    if mid is not None:
        return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': 'Method not found'}}
    return None

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
            continue
        out = handle(msg)
        if out is not None:
            print(json.dumps(out), flush=True)

if __name__ == '__main__':
    main()
