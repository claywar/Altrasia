# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x-alpha | Best effort |

## Threat model

Altrasia is designed as a **single-operator, local-first** narrative studio:

- Default bind: loopback (`127.0.0.1`)
- No multi-tenant isolation
- SQLite world data under `~/.altrasia/`

Do not expose the API to untrusted networks without authentication and TLS.

## Reporting vulnerabilities

Open a private security advisory on the project repository or contact maintainers directly. Do not file public issues for unpatched exploits.

## Operator responsibilities

- Keep `ALTRASIA_API_TOKEN` secret if set
- Restrict web-tool allowlists (`ALTRASIA_WEB_ALLOWLIST`) when enabling live fetch
- Review approval queue before approving `webtools_invoke` / `fs_write`
- AGPL-3.0 applies — see [LICENSE](LICENSE)

## Known limitations (Alpha)

- Mock LLM is default; real inference is operator-controlled
- Web fetch and FS tools are policy-gated but not a sandbox escape hatch for hostile prompts
- Plugins load local Python modules — only install trusted plugins
