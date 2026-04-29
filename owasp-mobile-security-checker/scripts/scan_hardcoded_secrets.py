#!/usr/bin/env python3
"""
Scan Flutter project for hardcoded secrets and credentials (OWASP M1).

This script searches for common patterns of hardcoded API keys, tokens,
passwords, and other sensitive credentials in Dart source files.
"""

import re
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple

# Patterns for detecting hardcoded secrets — (regex, label, severity)
SECRET_PATTERNS = [
    # API Keys and Tokens
    (r'api[_-]?key\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'API Key', 'HIGH'),
    (r'apikey\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'API Key', 'HIGH'),
    (r'api[_-]?secret\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'API Secret', 'HIGH'),
    (r'access[_-]?token\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'Access Token', 'HIGH'),
    (r'auth[_-]?token\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'Auth Token', 'HIGH'),
    (r'bearer\s+["\']([a-zA-Z0-9_\-\.]{20,})["\']', 'Bearer Token', 'HIGH'),

    # AWS Credentials
    (r'aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*["\']([A-Z0-9]{20})["\']', 'AWS Access Key', 'CRITICAL'),
    (r'aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\']([a-zA-Z0-9/+=]{40})["\']', 'AWS Secret Key', 'CRITICAL'),

    # Firebase
    (r'firebase[_-]?api[_-]?key\s*[:=]\s*["\']([a-zA-Z0-9_\-]{30,})["\']', 'Firebase API Key', 'HIGH'),

    # Database credentials
    (r'db[_-]?password\s*[:=]\s*["\']([^"\']+)["\']', 'Database Password', 'HIGH'),
    (r'database[_-]?url\s*[:=]\s*["\'][^"\']*:[^"\']*@[^"\']+["\']', 'Database URL with credentials', 'CRITICAL'),

    # Generic passwords
    (r'password\s*[:=]\s*["\']([^"\']{8,})["\']', 'Password', 'MEDIUM'),
    (r'passwd\s*[:=]\s*["\']([^"\']{8,})["\']', 'Password', 'MEDIUM'),
    (r'pwd\s*[:=]\s*["\']([^"\']{8,})["\']', 'Password', 'MEDIUM'),

    # Private keys
    (r'private[_-]?key\s*[:=]\s*["\']([^"\']+)["\']', 'Private Key', 'CRITICAL'),
    (r'-----BEGIN (?:RSA |DSA )?PRIVATE KEY-----', 'Private Key Block', 'CRITICAL'),

    # OAuth and Client Secrets
    (r'client[_-]?secret\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'Client Secret', 'HIGH'),
    (r'client[_-]?id\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'Client ID', 'MEDIUM'),

    # Generic secrets
    (r'secret[_-]?key\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', 'Secret Key', 'HIGH'),
    (r'encryption[_-]?key\s*[:=]\s*["\']([a-zA-Z0-9_\-/+=]{16,})["\']', 'Encryption Key', 'HIGH'),
]

# False positive patterns to exclude
FALSE_POSITIVE_PATTERNS = [
    r'example\.com',
    r'your[_-]api[_-]key',
    r'YOUR[_-]API[_-]KEY',
    r'<.*>',  # Placeholder patterns
    r'\$\{.*\}',  # Template variables
    r'FIXME',
    r'TODO',
    r'dummy',
    r'\btest\b',
    r'sample',
    r'placeholder',
]


def is_false_positive(value: str) -> bool:
    """Check if the detected value is likely a false positive."""
    value_lower = value.lower()
    for pattern in FALSE_POSITIVE_PATTERNS:
        if re.search(pattern, value_lower, re.IGNORECASE):
            return True
    return False


def scan_file(file_path: Path) -> List[Dict]:
    """Scan a single file for hardcoded secrets."""
    findings = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')

            in_block_comment = False
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()

                # Track block comments (Dart does not support nested /* */)
                if in_block_comment:
                    if '*/' in line:
                        in_block_comment = False
                    continue
                if stripped.startswith('/*'):
                    if '*/' not in line:
                        in_block_comment = True
                    continue

                # Skip single-line comments
                if stripped.startswith('//'):
                    continue

                for pattern, secret_type, severity in SECRET_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        value = match.group(1) if len(match.groups()) > 0 else match.group(0)

                        if is_false_positive(value):
                            continue

                        findings.append({
                            'file': str(file_path),
                            'line': line_num,
                            'type': secret_type,
                            'pattern': line.strip(),
                            'severity': severity,
                        })
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")

    return findings


def scan_project(project_root: str) -> Dict:
    """Scan entire Flutter project for hardcoded secrets."""
    project_path = Path(project_root)
    all_findings = []

    dart_files = list(project_path.glob('lib/**/*.dart'))
    gradle_files = list(project_path.glob('android/**/*.gradle'))
    plist_files = list(project_path.glob('ios/**/*.plist'))

    files_to_scan = dart_files + gradle_files + plist_files

    print(f"Scanning {len(files_to_scan)} files for hardcoded secrets...")

    for file_path in files_to_scan:
        findings = scan_file(file_path)
        all_findings.extend(findings)

    return {
        'total_files_scanned': len(files_to_scan),
        'total_findings': len(all_findings),
        'findings': all_findings
    }


def main():
    """Main execution function."""
    if len(sys.argv) < 2:
        project_root = os.getcwd()
    else:
        project_root = sys.argv[1]

    print(f"OWASP M1: Scanning for hardcoded secrets in {project_root}\n")

    results = scan_project(project_root)

    print(f"\n{'='*60}")
    print(f"Scan Results:")
    print(f"{'='*60}")
    print(f"Files scanned: {results['total_files_scanned']}")
    print(f"Potential secrets found: {results['total_findings']}\n")

    if results['findings']:
        print("Findings by type:")
        findings_by_type = {}
        for finding in results['findings']:
            secret_type = finding['type']
            findings_by_type[secret_type] = findings_by_type.get(secret_type, 0) + 1

        for secret_type, count in sorted(findings_by_type.items()):
            print(f"  - {secret_type}: {count}")

        print(f"\n{'='*60}")
        print("Detailed Findings:")
        print(f"{'='*60}\n")

        for i, finding in enumerate(results['findings'], 1):
            print(f"{i}. [{finding['severity']}] {finding['type']}")
            print(f"   File: {finding['file']}:{finding['line']}")
            print(f"   Code: {finding['pattern']}")
            print()

    # Save results to JSON
    output_file = Path(project_root) / 'owasp_m1_secrets_scan.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to: {output_file}")

    # Exit with error code only on CRITICAL/HIGH findings (consistent with other scanners)
    critical_high = sum(
        1 for f in results['findings'] if f.get('severity') in ('CRITICAL', 'HIGH')
    )
    sys.exit(1 if critical_high > 0 else 0)


if __name__ == '__main__':
    main()
