#!/usr/bin/env python3
"""Killfear One local MCP server (stdio). No key or input is stored.

Reads SURECHECK_API_KEY (required) and SURECHECK_BASE_URL (default
https://surecheck-live-040.onrender.com). Exposes check_phone, check_email, run_business_agent and run_aeo_agent and
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

BUSINESS_AGENTS = ['lead_cleaner', 'validator', 'outreach_drafter', 'reaction_checker', 'sequence_builder', 'page_builder', 'reporter']

TOOLS = [
    {'name': 'check_phone',
     'description': 'Validate a phone number with Killfear One numbering-plan metadata. Not live carrier, reachability, or ownership.',
     'inputSchema': {'type': 'object', 'properties': {
         'phone_number': {'type': 'string', 'description': 'Number, ideally E.164 (+...)', 'maxLength': 64},
         'country_code': {'type': 'string', 'description': 'Optional 2-letter region', 'maxLength': 2}},
         'required': ['phone_number'], 'additionalProperties': False}},
    {'name': 'check_email',
     'description': 'Validate an email with Killfear One syntax and DNS checks. Does not prove mailbox existence or delivery.',
     'inputSchema': {'type': 'object', 'properties': {
         'email': {'type': 'string', 'maxLength': 320}},
         'required': ['email'], 'additionalProperties': False}},
    {'name': 'run_business_agent',
     'description': 'Run the Killfear One business agent on up to 10 leads from CSV text (a domain column is required). Inner agents: lead_cleaner, validator, outreach_drafter, reaction_checker, sequence_builder, page_builder, reporter. Returns counts, review-only drafts and sequences, and an optional HTML landing page draft. Nothing is sent. 1 credit per lead, +1 if page_builder is selected, 10 credits max per call.',
     'inputSchema': {'type': 'object', 'properties': {
         'csv': {'type': 'string', 'description': 'CSV text with a domain column; optional company, first_name, email', 'maxLength': 20000},
         'offer': {'type': 'string', 'description': 'One or two sentences on what you offer', 'maxLength': 500},
         'sender': {'type': 'string', 'description': 'Sign-off name for drafts', 'maxLength': 120},
         'icp': {'type': 'string', 'description': 'Optional comma-separated keywords a lead page should match', 'maxLength': 200},
         'agents': {'type': 'array', 'items': {'type': 'string', 'enum': BUSINESS_AGENTS}, 'maxItems': 7,
                    'description': 'Optional subset. Default runs all except page_builder. Needed agents are added and listed.'},
         'page_name': {'type': 'string', 'description': 'Heading for the landing page draft', 'maxLength': 80},
         'page_points': {'type': 'array', 'items': {'type': 'string', 'maxLength': 120}, 'maxItems': 5,
                         'description': 'Up to 5 short bullet points for the landing page draft'}},
         'required': ['csv', 'offer', 'sender'], 'additionalProperties': False}},
    {'name': 'run_aeo_agent',
     'description': 'Run the Killfear One AEO/SEO agent on a business website. Reads up to 3 public pages on one site plus robots.txt, sitemap.xml and llms.txt, runs rule-based SEO and AEO checks, and returns two scores, a prioritized fix list and review-only drafts (organization JSON-LD, FAQ JSON-LD skeleton, llms.txt, robots.txt snippet). Does not measure rankings or AI citations and changes nothing on the site. 3 credits per audit.',
     'inputSchema': {'type': 'object', 'properties': {
         'url': {'type': 'string', 'description': 'Public https or http address of the site or page to audit', 'maxLength': 300},
         'extra_urls': {'type': 'array', 'items': {'type': 'string', 'maxLength': 300}, 'maxItems': 2,
                        'description': 'Optional up to 2 more pages on the same host'}},
         'required': ['url'], 'additionalProperties': False}},
]

def note(msg):
    print(f'surecheck-mcp: {msg}', file=sys.stderr, flush=True)

def call_api(path, payload, timeout=20):
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
        with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout) as r:
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
        spec = schema['properties'][key]
        if spec['type'] == 'array':
            if not isinstance(value, list) or len(value) > spec['maxItems']:
                return False
            item = spec['items']
            for v in value:
                if not isinstance(v, str) or not v.strip():
                    return False
                if 'enum' in item and v not in item['enum']:
                    return False
                if 'maxLength' in item and len(v) > item['maxLength']:
                    return False
            continue
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
            'serverInfo': {'name': 'surecheck', 'version': '0.3.0'}}}
    if method == 'ping':
        return {'jsonrpc': '2.0', 'id': mid, 'result': {}}
    if method == 'tools/list':
        return {'jsonrpc': '2.0', 'id': mid, 'result': {'tools': TOOLS}}
    if method == 'tools/call':
        name = params.get('name')
        if name not in ('check_phone', 'check_email', 'run_business_agent', 'run_aeo_agent'):
            return rpc_error(mid, -32602, 'Unknown tool')
        args = params.get('arguments', {})
        if not validate_args(name, args):
            return rpc_error(mid, -32602, 'Invalid tool arguments')
        if name == 'run_business_agent':
            return {'jsonrpc': '2.0', 'id': mid, 'result': text_result(call_api('/api/v1/agent/business', args, timeout=120))}
        if name == 'run_aeo_agent':
            return {'jsonrpc': '2.0', 'id': mid, 'result': text_result(call_api('/api/v1/agent/aeo', args, timeout=90))}
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
