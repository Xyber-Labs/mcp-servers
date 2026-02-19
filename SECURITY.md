# Security Policy

## Scope

This security policy applies to all Xyber smart contracts deployed on Solana, related infrastructure, and SDK
implementations.

**This policy is published at:**

- **GitHub:** [SECURITY.md](https://github.com/Xyber-Labs/mcp-servers/security/policy)
- **Website:** [security.txt](https://xyber.inc/.well-known/security.txt) (RFC 9116)

## Reporting a Vulnerability

- **DO NOT** create public GitHub issues for security vulnerabilities
- **DO NOT** disclose vulnerabilities publicly before coordinated disclosure
- **DO NOT** exploit vulnerabilities beyond proof of concept

### 1. GitHub Private Vulnerability Reporting (Recommended)

[**Report a vulnerability**](https://github.com/Xyber-Labs/mcp-servers/security/advisories/new) — provide a helpful title
and detailed description of the problem.

### 2. Email Reporting

Send reports to: **security@xyber.inc**

**Please include:**

- **Repository name** where the vulnerability was found
- Vulnerability details and steps to reproduce
- Proof of concept (if available)
- **Your GitHub username** — so we can invite you to collaborate on the security advisory

**For encrypted communication:** Use our PGP public key below. See [REPORTING_GUIDE.md](./REPORTING_GUIDE.md) for step-by-step instructions.

**Xyber Security PGP Public Key:**

```
-----BEGIN PGP PUBLIC KEY BLOCK-----

mDMEaYXdoxYJKwYBBAHaRw8BAQdA5ZUVXAARZ3BeivL5Jp1fU2r64SREutwF/odL
OsFdZzq0Rlh5YmVyIFNlY3VyaXR5IFRlYW0gKFZ1bG5lcmFiaWxpdHkgUmVwb3J0
aW5nIEtleSkgPHNlY3VyaXR5QHh5YmVyLmluYz6IlgQTFgoAPhYhBIaxO1szvuRa
T7/SKIcDS/CiTRoiBQJphd2jAhsDBQkB4TOABQsJCAcCBhUKCQgLAgQWAgMBAh4B
AheAAAoJEIcDS/CiTRoi/e4BAJY0eiOaqUN745b/h+y5xroSXUcjT2Wz2m3x7W2G
bmHUAP9f+GEiwjmfhvK/wP/2U7XP+dT4bjNCbmEhtT8HEc1cDrg4BGmF3aMSCisG
AQQBl1UBBQEBB0BkUxJYPXusOQaPsjNnOZg0rZdGgCexubLsfryIyM+0SwMBCAeI
fgQYFgoAJhYhBIaxO1szvuRaT7/SKIcDS/CiTRoiBQJphd2jAhsMBQkB4TOAAAoJ
EIcDS/CiTRoi4BYA/R3++whBfwNVdEG4ufqNuvWn6slWLqamLiI1SBAmYzSgAPsG
Xg7dpR5JwJTx/Z1Ct6YFIJLGnOmmrNegMzYE3pu2AQ==
=hz4o
-----END PGP PUBLIC KEY BLOCK-----
```

**Fingerprint:** `86B1 3B5B 33BE E45A 4FBF D228 8703 4BF0 A24D 1A22`

**Key verification:** Verify fingerprint across multiple sources before encrypting sensitive reports:

- [security.pub.asc](./security.pub.asc) in this repository
- https://xyber.inc/security/security.pub.asc
- keys.openpgp.org (email verified): `gpg --keyserver keys.openpgp.org --recv-keys 86B13B5B33BEE45A4FBFD22887034BF0A24D1A22`

### 3. Discord

**Security channel:** https://discord.com/channels/1352248408634687623/1352275383524790332

For sensitive disclosures, encrypt messages using our PGP key.

## Response Timeline

1. **Acknowledgment:** Within 72 hours
2. **Initial Assessment:** Within 7 days
3. **Status Updates:** Regular updates via GitHub Security Advisory
4. **Coordinated Disclosure:** Mutually agreed timeline (default: 90 days)

## Disclosure Policy

We follow coordinated disclosure using GitHub Security Advisories. Reports create a private draft advisory for
collaboration. After fix deployment, the advisory is published with CVE assignment (if applicable) and reporter credit.

## Legal

By reporting vulnerabilities, you agree to:

- Provide reasonable time to address the issue before public disclosure
- Not exploit the vulnerability beyond proof of concept
- Act in good faith

We commit to:

- Not pursue legal action against good-faith security research
- Credit you in the published advisory (unless you prefer anonymity)

## Additional Information

**Bug Bounty Program:** Coming soon

**Security Audits:** In progress — reports will be published upon completion

**Published Advisories:** https://github.com/Xyber-Labs/mcp-servers/security/advisories

---

**Last Updated:** 2026-02-06