#!/usr/bin/env python3
"""
APPSIERRA Self-Healing System

Automatically analyzes test failures and generates patch diffs.

Features:
- Parses pytest output and JSON diagnostics
- Detects broken signals, schema mismatches, timing regressions
- Generates patch diffs with code context
- Outputs selfheal_report.json with actionable recommendations

Usage:
    python selfheal.py [--diagnostics test_diagnostics.json] [--pytest-log pytest.log]
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# SECTION 1: DIAGNOSTIC PARSER
# ============================================================================


class DiagnosticParser:
    """Parse test diagnostics JSON"""

    def __init__(self, diagnostics_path: str = "test_diagnostics.json"):
        self.diagnostics_path = Path(diagnostics_path)
        self.data: dict = {}

        if self.diagnostics_path.exists():
            with open(self.diagnostics_path) as f:
                self.data = json.load(f)

    def get_broken_signals(self) -> list[dict]:
        """Get list of broken/disconnected signals"""
        signals = self.data.get("signals", [])
        return [s for s in signals if not s.get("connected", True)]

    def get_timing_violations(self) -> list[dict]:
        """Get timing events that exceeded thresholds"""
        timing = self.data.get("timing", [])
        return [t for t in timing if not t.get("passed", True)]

    def get_errors(self) -> list[dict]:
        """Get all test errors"""
        return self.data.get("errors", [])

    def get_db_failures(self) -> list[dict]:
        """Get database consistency check failures"""
        db_checks = self.data.get("db_checks", [])
        return [c for c in db_checks if not c.get("passed", True)]

    def get_summary(self) -> dict:
        """Get diagnostic summary"""
        return self.data.get("summary", {})


# ============================================================================
# SECTION 2: PYTEST LOG PARSER
# ============================================================================


class PytestLogParser:
    """Parse pytest output logs"""

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = Path(log_path) if log_path else None
        self.log_content = ""

        if self.log_path and self.log_path.exists():
            self.log_content = self.log_path.read_text()

    def extract_failures(self) -> list[dict]:
        """Extract failed tests from pytest output"""
        failures = []

        # Pattern: FAILED tests/test_file.py::TestClass::test_method
        pattern = r"FAILED ([\w/.]+)::([\w:]+) - (.+)"

        for match in re.finditer(pattern, self.log_content):
            failures.append({"file": match.group(1), "test": match.group(2), "reason": match.group(3)})

        return failures

    def extract_errors(self) -> list[dict]:
        """Extract error messages from pytest output"""
        errors = []

        # Pattern: ERROR tests/test_file.py::TestClass::test_method
        pattern = r"ERROR ([\w/.]+)::([\w:]+)"

        for match in re.finditer(pattern, self.log_content):
            errors.append({"file": match.group(1), "test": match.group(2)})

        return errors

    def get_coverage_percentage(self) -> Optional[float]:
        """Extract coverage percentage from pytest output"""
        # Pattern: TOTAL     1234     567    46%
        pattern = r"TOTAL\s+\d+\s+\d+\s+(\d+)%"
        match = re.search(pattern, self.log_content)

        if match:
            return float(match.group(1))
        return None


# ============================================================================
# SECTION 3: ISSUE DETECTOR
# ============================================================================


class IssueDetector:
    """Detect specific issues from diagnostics and logs"""

    def __init__(self, diag_parser: DiagnosticParser, log_parser: PytestLogParser):
        self.diag = diag_parser
        self.log = log_parser

    def detect_broken_signals(self) -> list[dict]:
        """Detect broken signal connections"""
        issues = []
        broken = self.diag.get_broken_signals()

        for signal in broken:
            issues.append(
                {
                    "type": "BrokenSignal",
                    "severity": "HIGH",
                    "component": signal.get("sender"),
                    "signal_name": signal.get("signal"),
                    "description": f"Signal {signal.get('signal')} from {signal.get('sender')} to {signal.get('receiver')} is not connected",
                    "recommendation": f"Connect {signal.get('signal')} in AppManager._setup_cross_panel_linkage()",
                    "auto_fix": True,
                }
            )

        return issues

    def detect_timing_regressions(self) -> list[dict]:
        """Detect timing violations"""
        issues = []
        violations = self.diag.get_timing_violations()

        for timing in violations:
            duration = timing.get("duration_ms", 0)
            threshold = timing.get("threshold_ms", 100)
            event = timing.get("event", "unknown")

            issues.append(
                {
                    "type": "TimingRegression",
                    "severity": "MEDIUM",
                    "component": event,
                    "description": f"Event '{event}' took {duration:.2f}ms, exceeding {threshold}ms threshold",
                    "recommendation": f"Optimize {event} to improve performance",
                    "auto_fix": False,
                    "metrics": {"actual_ms": duration, "threshold_ms": threshold, "over_by_ms": duration - threshold},
                }
            )

        return issues

    def detect_schema_mismatches(self) -> list[dict]:
        """Detect schema mismatches from errors"""
        issues = []
        errors = self.diag.get_errors()

        for error in errors:
            if "schema" in error.get("message", "").lower() or "keyerror" in error.get("error_type", "").lower():
                issues.append(
                    {
                        "type": "SchemaMismatch",
                        "severity": "HIGH",
                        "component": error.get("test"),
                        "description": f"Schema mismatch: {error.get('message')}",
                        "recommendation": "Verify DTC message schema matches expected format",
                        "auto_fix": False,
                    }
                )

        return issues

    def detect_db_issues(self) -> list[dict]:
        """Detect database consistency issues"""
        issues = []
        db_failures = self.diag.get_db_failures()

        for failure in db_failures:
            issues.append(
                {
                    "type": "DatabaseIssue",
                    "severity": "CRITICAL",
                    "component": "Database",
                    "description": f"DB check failed: {failure.get('message')}",
                    "recommendation": "Run database migration or VACUUM command",
                    "auto_fix": False,
                }
            )

        return issues

    def detect_all_issues(self) -> list[dict]:
        """Detect all issues"""
        issues = []
        issues.extend(self.detect_broken_signals())
        issues.extend(self.detect_timing_regressions())
        issues.extend(self.detect_schema_mismatches())
        issues.extend(self.detect_db_issues())
        return issues


# ============================================================================
# SECTION 4: PATCH GENERATOR
# ============================================================================


class PatchGenerator:
    """Generate patch diffs for auto-fixable issues"""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root

    def generate_signal_connection_patch(self, issue: dict) -> Optional[dict]:
        """Generate patch to fix broken signal connection"""
        signal_name = issue.get("signal_name", "")
        sender = issue.get("component", "")

        # Read app_manager.py
        app_manager_file = self.project_root / "core" / "app_manager.py"
        if not app_manager_file.exists():
            return None

        content = app_manager_file.read_text()
        lines = content.splitlines()

        # Find _setup_cross_panel_linkage method
        method_line = None
        for i, line in enumerate(lines):
            if "def _setup_cross_panel_linkage" in line:
                method_line = i
                break

        if method_line is None:
            return None

        # Generate patch
        patch_line = f"        # TODO: Connect {signal_name} from {sender}"
        context_start = max(0, method_line - 3)
        context_end = min(len(lines), method_line + 10)

        return {
            "file": "core/app_manager.py",
            "line": method_line,
            "context_before": lines[context_start:method_line],
            "patch": [patch_line],
            "context_after": lines[method_line:context_end],
            "description": f"Add connection for {signal_name}",
        }

    def generate_patches(self, issues: list[dict]) -> list[dict]:
        """Generate patches for all auto-fixable issues"""
        patches = []

        for issue in issues:
            if not issue.get("auto_fix", False):
                continue

            if issue["type"] == "BrokenSignal":
                patch = self.generate_signal_connection_patch(issue)
                if patch:
                    patches.append(patch)

        return patches


# ============================================================================
# SECTION 5: REPORT GENERATOR
# ============================================================================


class SelfHealReportGenerator:
    """Generate comprehensive self-healing report"""

    def __init__(self, issues: list[dict], patches: list[dict], diagnostics: dict):
        self.issues = issues
        self.patches = patches
        self.diagnostics = diagnostics

    def generate_report(self) -> dict:
        """Generate complete self-healing report"""
        # Group issues by type
        issues_by_type = {}
        for issue in self.issues:
            issue_type = issue["type"]
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        # Calculate severity counts
        severity_counts = {
            "CRITICAL": sum(1 for i in self.issues if i["severity"] == "CRITICAL"),
            "HIGH": sum(1 for i in self.issues if i["severity"] == "HIGH"),
            "MEDIUM": sum(1 for i in self.issues if i["severity"] == "MEDIUM"),
            "LOW": sum(1 for i in self.issues if i["severity"] == "LOW"),
        }

        # Get auto-fixable count
        auto_fixable = sum(1 for i in self.issues if i.get("auto_fix", False))

        report = {
            "generated": datetime.now().isoformat(),
            "summary": {
                "total_issues": len(self.issues),
                "auto_fixable": auto_fixable,
                "patches_generated": len(self.patches),
                "severity_breakdown": severity_counts,
            },
            "issues_by_type": issues_by_type,
            "patches": self.patches,
            "diagnostics_summary": self.diagnostics.get("summary", {}),
            "recommendations": self._generate_recommendations(),
        }

        return report

    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Check timing violations
        timing_issues = [i for i in self.issues if i["type"] == "TimingRegression"]
        if timing_issues:
            recommendations.append(
                f"Performance: {len(timing_issues)} timing violations detected. "
                "Consider optimizing hot paths and reducing UI blocking operations."
            )

        # Check broken signals
        signal_issues = [i for i in self.issues if i["type"] == "BrokenSignal"]
        if signal_issues:
            recommendations.append(
                f"Signals: {len(signal_issues)} broken signal connections. "
                "Review AppManager._setup_cross_panel_linkage() and reconnect signals."
            )

        # Check DB issues
        db_issues = [i for i in self.issues if i["type"] == "DatabaseIssue"]
        if db_issues:
            recommendations.append(
                f"Database: {len(db_issues)} consistency issues. "
                "Run PRAGMA integrity_check and consider rebuilding database."
            )

        return recommendations

    def export_json(self, output_path: str = "selfheal_report.json"):
        """Export report to JSON file"""
        report = self.generate_report()
        output_file = Path(output_path)
        output_file.write_text(json.dumps(report, indent=2))
        return str(output_file.absolute())

    def print_summary(self):
        """Print human-readable summary"""
        report = self.generate_report()

        print("\n" + "=" * 80)
        print("SELF-HEALING REPORT SUMMARY")
        print("=" * 80)
        print(f"Generated: {report['generated']}")
        print(f"\nTotal Issues: {report['summary']['total_issues']}")
        print(f"Auto-Fixable: {report['summary']['auto_fixable']}")
        print(f"Patches Generated: {report['summary']['patches_generated']}")

        print("\nSeverity Breakdown:")
        for severity, count in report["summary"]["severity_breakdown"].items():
            if count > 0:
                print(f"  {severity}: {count}")

        print("\nIssues by Type:")
        for issue_type, issues in report["issues_by_type"].items():
            print(f"  {issue_type}: {len(issues)}")

        if report["recommendations"]:
            print("\nRecommendations:")
            for i, rec in enumerate(report["recommendations"], 1):
                print(f"  {i}. {rec}")

        print("=" * 80 + "\n")


# ============================================================================
# SECTION 6: MAIN RUNNER
# ============================================================================


def main():
    """Main self-healing runner"""
    parser = argparse.ArgumentParser(description="APPSIERRA Self-Healing System")
    parser.add_argument("--diagnostics", default="test_diagnostics.json", help="Path to test diagnostics JSON file")
    parser.add_argument("--pytest-log", default=None, help="Path to pytest log file (optional)")
    parser.add_argument("--output", default="selfheal_report.json", help="Output path for self-healing report")

    args = parser.parse_args()

    print("\n[SELFHEAL] Initializing self-healing system...")

    # Parse diagnostics
    diag_parser = DiagnosticParser(args.diagnostics)
    print(f"[SELFHEAL] Loaded diagnostics from: {args.diagnostics}")

    # Parse pytest log (if provided)
    log_parser = PytestLogParser(args.pytest_log)
    if args.pytest_log:
        print(f"[SELFHEAL] Loaded pytest log from: {args.pytest_log}")

    # Detect issues
    print("[SELFHEAL] Detecting issues...")
    detector = IssueDetector(diag_parser, log_parser)
    issues = detector.detect_all_issues()
    print(f"[SELFHEAL] Found {len(issues)} issues")

    # Generate patches
    print("[SELFHEAL] Generating patches...")
    patch_gen = PatchGenerator()
    patches = patch_gen.generate_patches(issues)
    print(f"[SELFHEAL] Generated {len(patches)} patches")

    # Generate report
    print("[SELFHEAL] Generating report...")
    report_gen = SelfHealReportGenerator(issues, patches, diag_parser.data)

    # Export report
    output_path = report_gen.export_json(args.output)
    print(f"[SELFHEAL] Report exported to: {output_path}")

    # Print summary
    report_gen.print_summary()

    # Exit code based on severity
    critical_issues = sum(1 for i in issues if i["severity"] == "CRITICAL")
    if critical_issues > 0:
        print(f"[SELFHEAL] CRITICAL: {critical_issues} critical issues found!")
        sys.exit(2)
    elif len(issues) > 0:
        print(f"[SELFHEAL] WARNING: {len(issues)} issues found")
        sys.exit(1)
    else:
        print("[SELFHEAL] SUCCESS: No issues detected!")
        sys.exit(0)


if __name__ == "__main__":
    main()
