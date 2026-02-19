---
name: owasp-mobile-security-checker
description: Use when performing security audits, vulnerability assessments, or compliance checks on Flutter or mobile applications. Covers OWASP Mobile Top 10 (2024) — hardcoded secrets (M1), insecure storage (M9), weak cryptography (M10), network issues (M5), and 6 more categories with automated scanners and remediation guidance.
compatibility: Requires Python 3 for automated scanners. Flutter/Dart project with pubspec.yaml. Android and/or iOS targets. Run scripts from the project root directory.
metadata:
  author: harish
  version: 1.0.0
---

# OWASP Mobile Security Checker

Comprehensive security analysis for Flutter and mobile applications based on OWASP Mobile Top 10 (2024).

## Automated Scanners

Four Python scanners cover the most automatable risk categories. Replace `<skill-dir>` with the skill's install path (e.g. `~/.claude/skills/owasp-mobile-security-checker`):

### M1 — Hardcoded Secrets

```bash
python3 <skill-dir>/scripts/scan_hardcoded_secrets.py /path/to/project
```

Detects API keys, tokens, passwords, AWS credentials, and Firebase keys in Dart code and config files.

### M2 — Dependency Vulnerabilities

```bash
python3 <skill-dir>/scripts/check_dependencies.py /path/to/project
```

Analyzes `pubspec.yaml` for outdated packages, `any` version constraints, and known CVEs.

### M5 — Network Security

```bash
python3 <skill-dir>/scripts/check_network_security.py /path/to/project
```

Checks HTTP vs HTTPS usage, certificate pinning, Android Network Security Config, and iOS ATS settings.

### M9 — Insecure Storage

```bash
python3 <skill-dir>/scripts/analyze_storage_security.py /path/to/project
```

Identifies unencrypted SharedPreferences, plaintext file storage, unencrypted databases, and insecure backup configurations.

## Manual Analysis

M3, M4, M6, M7, M8, and M10 require code review. See `references/owasp_mobile_top_10_2024.md` for Flutter-specific vulnerability patterns, attack flows, and remediation for each category.

## Workflow

```text
Is this a comprehensive audit?
├─ YES → Run all 4 scanners → Review JSON outputs → Manual analysis (M3/M4/M6/M7/M8/M10) → Generate report
└─ NO → Continue...

Specific risk category?
├─ M1 → scan_hardcoded_secrets.py
├─ M2 → check_dependencies.py
├─ M5 → check_network_security.py
├─ M9 → analyze_storage_security.py
└─ M3/M4/M6/M7/M8/M10 → references/owasp_mobile_top_10_2024.md → manual analysis

Quick pre-release check?
└─ YES → Run all 4 scanners → Fix CRITICAL and HIGH findings only
```

## Quick Start: Full Audit

```bash
# Run all automated scanners from the project root
python3 <skill-dir>/scripts/scan_hardcoded_secrets.py .
python3 <skill-dir>/scripts/check_dependencies.py .
python3 <skill-dir>/scripts/check_network_security.py .
python3 <skill-dir>/scripts/analyze_storage_security.py .

# Outputs produced:
#   owasp_m1_secrets_scan.json
#   owasp_m2_dependencies_scan.json
#   owasp_m5_network_scan.json
#   owasp_m9_storage_scan.json
```

1. **Prioritise by severity** — fix CRITICAL and HIGH before release
2. **For M3, M4, M6, M7, M8, M10** — see `references/owasp_mobile_top_10_2024.md`
3. **Generate remediation plan** with code examples and timeline

## OWASP Mobile Top 10 (2024) — Quick Reference

| Risk | Issue | Automated? | Key Check |
| --- | --- | --- | --- |
| **M1** | Hardcoded credentials | ✅ scanner | API keys, tokens in source/config |
| **M2** | Vulnerable dependencies | ✅ scanner | Outdated or unconstrained packages |
| **M3** | Weak authentication | Manual | Token storage, MFA, session expiry |
| **M4** | Input validation | Manual | SQL injection, XSS in WebViews, IDOR |
| **M5** | Insecure communication | ✅ scanner | HTTP usage, missing cert pinning |
| **M6** | Privacy violations | Manual | PII in logs/analytics, excess permissions |
| **M7** | No binary protections | Manual | Missing `--obfuscate`, no root detection |
| **M8** | Misconfiguration | Manual | Debug flags in production, verbose logging |
| **M9** | Insecure storage | ✅ scanner | Sensitive data in SharedPreferences |
| **M10** | Weak cryptography | Manual | MD5/SHA1/ECB usage, hardcoded keys |

## Understanding Scan Results

| Severity | Meaning | Action |
| --- | --- | --- |
| **CRITICAL** | Exploitable immediately | Fix now — do not release |
| **HIGH** | Significant vulnerability | Fix before release |
| **MEDIUM** | Should be addressed | Plan for next sprint |
| **LOW** | Best practice improvement | Address as time permits |

### Common False Positives

- **M1**: Test/example keys, placeholders like `YOUR_API_KEY`
- **M2**: Dev-only dependencies (linters, test tools)
- **M5**: HTTP for `localhost`/`127.0.0.1` in development
- **M9**: Non-sensitive data in SharedPreferences (theme preference, language)

Always verify findings in context before flagging as vulnerabilities.

## When NOT to Use

- Web application security audits — this skill is mobile/Flutter-specific
- Backend API or server security reviews
- As a substitute for professional penetration testing or a formal security audit
- Projects that do not use Flutter/Dart or `pubspec.yaml`

## Reference Documentation

`references/owasp_mobile_top_10_2024.md` provides per-risk detail:

- Real-world attack scenarios and examples
- Flutter-specific vulnerability patterns (Dart code)
- Insecure vs secure code examples
- Platform-specific guidance (Android Keystore/NSC, iOS Keychain/ATS)
- Full mitigation strategies

## Integration Points

| Stage | Action |
| --- | --- |
| Pre-commit | Run `scan_hardcoded_secrets.py` as a lightweight secrets gate |
| Pull requests | Run all 4 scanners, post findings as PR comment |
| Release builds | Full audit including manual analysis for all 10 categories |
| Incident response | Run targeted scanner for the reported vulnerability category |
