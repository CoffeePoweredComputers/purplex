# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Purplex, please report it responsibly. **Do not open a public issue.**

### How to Report

1. **Preferred:** Use [GitHub Security Advisories](../../security/advisories/new) to report the vulnerability privately.
2. **Alternative:** Email the maintainers directly (see the repository's profile for contact information).

### What to Include

- A description of the vulnerability
- Steps to reproduce the issue
- The potential impact
- Any suggested fixes (optional)

### Response Timeline

- **Acknowledgment:** Within 72 hours of receiving the report
- **Initial assessment:** Within 1 week
- **Fix or mitigation:** Dependent on severity, but we aim for:
  - Critical: Within 48 hours
  - High: Within 1 week
  - Medium/Low: Within the next release cycle

## Scope

This security policy applies to:
- The Purplex application code (backend and frontend)
- Docker-based code execution sandbox configuration
- Authentication and authorization logic
- Data privacy and protection mechanisms

## Security Considerations

Purplex executes untrusted user code in Docker containers. The sandbox is designed with:
- Resource limits (CPU, memory, time)
- Network isolation
- Read-only filesystem access
- Non-root execution

If you find a way to escape the sandbox or access resources outside the container, this is a critical vulnerability and we ask that you report it immediately.

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | Yes                |
| < 0.1   | No                 |
