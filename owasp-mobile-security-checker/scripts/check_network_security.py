#!/usr/bin/env python3
"""
Check network security configurations (OWASP M5).

This script analyzes Flutter project for:
- HTTP vs HTTPS usage
- Certificate pinning implementation
- Network security configuration
- WebSocket security
"""

import re
import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict


def scan_http_usage(file_path: Path) -> List[Dict]:
    """Scan for insecure HTTP usage instead of HTTPS."""
    findings = []

    http_patterns = [
        (r'http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)', 'HTTP URL (non-localhost)'),
        (r'["\']http:["\']', 'HTTP scheme'),
        (r'ws://', 'Insecure WebSocket'),
    ]

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.read().split('\n')

        in_block_comment = False
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if in_block_comment:
                if '*/' in line:
                    in_block_comment = False
                continue
            if stripped.startswith('/*'):
                if '*/' not in line:
                    in_block_comment = True
                continue
            if stripped.startswith('//'):
                continue

            for pattern, issue_type in http_patterns:
                for _ in re.finditer(pattern, line, re.IGNORECASE):
                    findings.append({
                        'file': str(file_path),
                        'line': line_num,
                        'issue': issue_type,
                        'code': stripped,
                        'severity': 'HIGH',
                        'recommendation': 'Use HTTPS/WSS instead of HTTP/WS',
                    })

    except Exception as e:
        print(f"Error scanning {file_path}: {e}")

    return findings


def check_bad_cert_callback(file_path: Path) -> List[Dict]:
    """Check for dangerous badCertificateCallback that accepts all certificates."""
    findings = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if re.search(r'badCertificateCallback.*=.*\(.*\).*=>.*true', content):
            findings.append({
                'file': str(file_path),
                'line': 0,
                'issue': 'Certificate validation disabled (accepts all certificates)',
                'code': 'badCertificateCallback = (...) => true',
                'severity': 'CRITICAL',
                'recommendation': 'Remove this in production or implement proper certificate pinning',
            })
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
    return findings


def check_http_client_pinning(project_root: Path, dart_files: List[Path]) -> List[Dict]:
    """Project-level check: report once if HttpClient is used without a pinning package."""
    uses_http_client = False
    for file_path in dart_files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                if 'HttpClient' in f.read():
                    uses_http_client = True
                    break
        except Exception:
            pass

    if not uses_http_client:
        return []

    pubspec_path = project_root / 'pubspec.yaml'
    has_pinning_package = False
    if pubspec_path.exists():
        try:
            content = pubspec_path.read_text()
            has_pinning_package = any(pkg in content for pkg in [
                'http_certificate_pinning',
                'cert_pinning',
                'ssl_pinning_plugin',
            ])
        except Exception:
            pass

    if has_pinning_package:
        return []

    return [{
        'file': 'pubspec.yaml',
        'line': 0,
        'issue': 'HttpClient used without a certificate pinning package',
        'code': 'No http_certificate_pinning / ssl_pinning_plugin found in pubspec.yaml',
        'severity': 'MEDIUM',
        'recommendation': 'Consider implementing certificate pinning for sensitive APIs',
    }]


def check_android_network_security(project_root: Path) -> List[Dict]:
    """Check Android network security configuration."""
    findings = []

    network_security_config = project_root / 'android' / 'app' / 'src' / 'main' / 'res' / 'xml' / 'network_security_config.xml'

    if not network_security_config.exists():
        findings.append({
            'file': 'android/app/src/main/res/xml/network_security_config.xml',
            'line': 0,
            'issue': 'Network security configuration not found',
            'code': 'Missing file',
            'severity': 'MEDIUM',
            'recommendation': 'Create network_security_config.xml to enforce HTTPS and certificate pinning'
        })
        return findings

    try:
        tree = ET.parse(network_security_config)
        root = tree.getroot()

        # Check for cleartextTrafficPermitted
        base_config = root.find('.//base-config')
        if base_config is not None:
            cleartext = base_config.get('cleartextTrafficPermitted')
            if cleartext == 'true':
                findings.append({
                    'file': str(network_security_config),
                    'line': 0,
                    'issue': 'Cleartext traffic permitted globally',
                    'code': 'cleartextTrafficPermitted="true"',
                    'severity': 'HIGH',
                    'recommendation': 'Disable cleartext traffic or limit to specific domains'
                })

        # Check for certificate pinning
        has_pinning = root.findall('.//pin-set')
        if not has_pinning:
            findings.append({
                'file': str(network_security_config),
                'line': 0,
                'issue': 'No certificate pinning configured',
                'code': 'No <pin-set> elements found',
                'severity': 'MEDIUM',
                'recommendation': 'Configure certificate pinning for production APIs'
            })

    except Exception as e:
        print(f"Error parsing network security config: {e}")

    return findings


def check_ios_ats_configuration(project_root: Path) -> List[Dict]:
    """Check iOS App Transport Security configuration."""
    findings = []

    info_plist = project_root / 'ios' / 'Runner' / 'Info.plist'

    if not info_plist.exists():
        return findings

    try:
        with open(info_plist, 'r') as f:
            content = f.read()

            # Check if ATS is disabled globally
            if 'NSAllowsArbitraryLoads' in content:
                # Extract the value
                if re.search(r'NSAllowsArbitraryLoads.*<true/>', content, re.DOTALL):
                    findings.append({
                        'file': str(info_plist),
                        'line': 0,
                        'issue': 'App Transport Security disabled globally',
                        'code': 'NSAllowsArbitraryLoads = true',
                        'severity': 'CRITICAL',
                        'recommendation': 'Enable ATS and use NSExceptionDomains for specific cases only'
                    })

            # Check for local networking allowance
            if 'NSAllowsLocalNetworking' in content:
                findings.append({
                    'file': str(info_plist),
                    'line': 0,
                    'issue': 'Local networking allowed',
                    'code': 'NSAllowsLocalNetworking',
                    'severity': 'LOW',
                    'recommendation': 'Ensure this is intentional and only for development'
                })

    except Exception as e:
        print(f"Error scanning Info.plist: {e}")

    return findings


def scan_project(project_root: str) -> Dict:
    """Scan entire Flutter project for network security issues."""
    project_path = Path(project_root)
    all_findings = []

    # Get all Dart files
    dart_files = list(project_path.glob('lib/**/*.dart'))

    print(f"Scanning {len(dart_files)} Dart files for network security issues...")

    for file_path in dart_files:
        all_findings.extend(scan_http_usage(file_path))
        all_findings.extend(check_bad_cert_callback(file_path))

    # Project-level pinning check — emits one finding, not one per file
    all_findings.extend(check_http_client_pinning(project_path, dart_files))

    all_findings.extend(check_android_network_security(project_path))
    all_findings.extend(check_ios_ats_configuration(project_path))

    return {
        'total_files_scanned': len(dart_files),
        'total_findings': len(all_findings),
        'findings': all_findings
    }


def main():
    """Main execution function."""
    project_root = sys.argv[1] if len(sys.argv) > 1 else '.'

    print(f"OWASP M5: Analyzing network security in {project_root}\n")

    results = scan_project(project_root)

    # Group by severity (always initialised so the exit-code line is always safe)
    by_severity: Dict[str, List] = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': []}
    for finding in results['findings']:
        by_severity.setdefault(finding.get('severity', 'MEDIUM'), []).append(finding)

    print(f"\n{'='*60}")
    print("Network Security Scan Results:")
    print(f"{'='*60}")
    print(f"Files scanned: {results['total_files_scanned']}")
    print(f"Issues found: {results['total_findings']}\n")

    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if by_severity[severity]:
            print(f"\n{severity} Severity ({len(by_severity[severity])}):")
            print('-' * 60)
            for i, finding in enumerate(by_severity[severity], 1):
                print(f"\n{i}. {finding['issue']}")
                print(f"   File: {finding['file']}:{finding['line']}")
                if finding.get('code'):
                    print(f"   Code: {finding['code']}")
                print(f"   Recommendation: {finding['recommendation']}")

    # Save results
    output_file = Path(project_root) / 'owasp_m5_network_scan.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")

    critical_high = len(by_severity['CRITICAL']) + len(by_severity['HIGH'])
    sys.exit(1 if critical_high > 0 else 0)


if __name__ == '__main__':
    main()
