# Killfear One MCP server: tools for AI agents: phone check, email check and a small-business lead agent (0.2.0)
Phone checks return numbering-plan metadata; email checks are syntax/DNS only. Local stdio MCP server; Python 3.8+. No third-party runtime dependencies.

Download the wheel from the GitHub release for 0.2.0, then:
python3 -m venv .venv
.venv/bin/python -m pip install --no-index ./surecheck_mcp-0.2.0-py3-none-any.whl

Windows uses .venv\Scripts\python.exe and .venv\Scripts\surecheck-mcp.exe.
Register the absolute path to .venv/bin/surecheck-mcp (Windows: .venv\Scripts\surecheck-mcp.exe) as the client command, with SURECHECK_API_KEY in its environment. No args required.
Default SURECHECK_BASE_URL: https://surecheck-live-040.onrender.com

Alternatively, the older 0.1.1 .mcpb bundle (2 check tools only; no 0.2.0 bundle yet) can be opened in an MCPB-capable client and enter the API key in its secure settings. Python must be installed as python3 on macOS/Linux or python on Windows. Bundle is unsigned. Desktop GUI install has not been tested on macOS/Windows; manifest validation and extracted-bundle subprocess launch have been tested on Linux.

Supported transport: stdio only. No remote MCP endpoint, SSE, Streamable HTTP, OAuth, PyPI or npm publication. Protocol negotiation: 2024-11-05, 2025-03-26, 2025-06-18.
Tools: check_phone(phone_number, country_code?), check_email(email), run_business_agent(csv, offer, sender, icp?, agents?, page_name?, page_points?).
run_business_agent calls the Killfear One business agent: up to 10 leads per call, 1 credit per lead (+1 if page_builder is selected). It returns review-only drafts and sequences and an optional HTML landing page draft. Nothing is sent and nothing is stored by the wrapper.
Version 0.2.0 adds run_business_agent. The wheel is built; the .mcpb bundle was not rebuilt and stays at 0.1.1 (2 tools).
Results preserve null/unknown/error states. Phone checks are numbering-plan metadata only, not live carrier, HLR, reachability or ownership. Email checks are syntax/DNS only, not mailbox, catch-all or delivery verification.
New API keys require a paid plan: $29/mo for 10,000 checks, $79/mo for 50,000. Keys from the earlier free beta keep their remaining checks. Host can sleep; a first request can time out. Retry after it wakes.
The local wrapper stores no inputs or keys. It transmits the key and requested phone/email to Killfear One over HTTPS. DNS checks send the domain to DNS infrastructure. The host/client can keep logs according to their own settings; do not submit sensitive personal data without permission. Inputs are not saved to the API application database or access logs; account/key hashes and usage accounting are stored. Use synthetic data for demos.
0.2.0 adds the run_business_agent tool. Drafts, sequences and pages it returns are for human review; the server sends no email, SMS or posts.

## Container (stdio)

A Dockerfile is included for clients that can run local stdio containers:

```sh
docker build -t surecheck-mcp .
docker run --rm -i -e SURECHECK_API_KEY surecheck-mcp
```

Set SURECHECK_API_KEY in the calling environment before running. Do not put the
key in the Dockerfile or image. The container runs as an unprivileged user.
Container build and execution are not yet verified. Including a Dockerfile does
not establish compatibility with Glama's deployment service. No remote endpoint
or HTTP transport is provided by this container.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The offline suite checks malformed input recovery, argument checks, protocol
negotiation, HTTPS-only configuration, blocked redirects and error handling.
API responses are mocked. The suite does not verify live paid provisioning.
