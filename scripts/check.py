#!/usr/bin/env python3
"""Code Quality Check Script for MCPnp

This script runs comprehensive code quality checks including:
- Black formatting validation
- Ruff linting and code analysis
- Pytest test execution

Usage:
    python check.py [--fix] [--quick]

Options:
    --fix    Apply black formatting and ruff fixes automatically
    --quick  Run quick checks (skip some slower tests)
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status with timing."""
    print(f"\n{'='*60}")
    print(f"🔍 {description}")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,  # 5 minute timeout
            check=False,
        )

        duration = time.time() - start_time

        if result.returncode == 0:
            print(f"✅ PASSED ({duration:.2f}s)")
            if result.stdout.strip():
                print(f"\nOutput:\n{result.stdout}")
            return True
        print(f"❌ FAILED ({duration:.2f}s)")
        if result.stdout.strip():
            print(f"\nSTDOUT:\n{result.stdout}")
        if result.stderr.strip():
            print(f"\nSTDERR:\n{result.stderr}")
        return False

    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT after 5 minutes")
        return False
    except subprocess.CalledProcessError as e:
        print(f"💥 ERROR: {e}")
        return False
    except FileNotFoundError:
        print(f"🚫 COMMAND NOT FOUND: {cmd[0]}")
        return False


def main():
    """Run all code quality checks."""
    fix_mode = "--fix" in sys.argv
    quick_mode = "--quick" in sys.argv

    print("🚀 MCPnp Code Quality Checker")
    print(f"📁 Working Directory: {Path.cwd()}")
    print(f"🔧 Fix Mode: {'ON' if fix_mode else 'OFF'}")
    print(f"⚡ Quick Mode: {'ON' if quick_mode else 'OFF'}")

    # Track results
    results = {}
    start_time = time.time()

    # 1. Black Formatting Check
    black_cmd = ["uv", "run", "black"]
    if not fix_mode:
        black_cmd.extend(["--check", "--diff"])
    black_cmd.extend([".", "--exclude", ".venv"])

    results["black"] = run_command(
        black_cmd,
        "Black Code Formatting" + (" (Fix Mode)" if fix_mode else " (Check Mode)"),
    )

    # 2. Ruff Analysis
    ruff_targets = [
        "bin/",
        "scripts/",
        "tests/",
        "app_flask.py",
        "auth_session.py",
        "config.py",
        "constants.py",
        "datastore_postgresql.py",
        "db.py",
        "db_schema_definitions.py",
        "db_setup.py",
        "db_setup_shared.py",
        "error_utils.py",
        "i18n.py",
        "mcp_server.py",
        "mcp_tool_router.py",
        "mcp_tools.py",
        "pantry_manager_abc.py",
        "pantry_manager_factory.py",
        "pantry_manager_shared.py",
        "pantry_manager_sqlite.py",
        "recipe_mcp_server.py",
        "web_auth_simple.py",
        "wsgi.py",
    ]
    if quick_mode:
        ruff_targets = ["mcpnp/"]  # Skip tests in quick mode

    ruff_cmd = ["uv", "run", "ruff", "check"] + ruff_targets
    if fix_mode:
        ruff_cmd.append("--fix")

    results["ruff"] = run_command(
        ruff_cmd,
        "Ruff Code Analysis"
        + (" (Fix Mode)" if fix_mode else "")
        + (" (Quick)" if quick_mode else ""),
    )

    # 3. Pytest Test Execution
    pytest_cmd = ["uv", "run", "pytest", "tests/"]
    if quick_mode:
        pytest_cmd.extend(["--tb=line", "-q", "-x"])  # Stop on first failure

    results["pytest"] = run_command(
        pytest_cmd, "Pytest Test Execution" + (" (Quick)" if quick_mode else "")
    )

    # Summary Report
    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print("📊 FINAL RESULTS")
    print(f"{'='*60}")

    passed = sum(results.values())
    total = len(results)

    for check, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check.upper():<10} {'PASSED' if status else 'FAILED'}")

    print(f"\n🎯 Overall: {passed}/{total} checks passed")
    print(f"⏱️  Total time: {total_time:.2f}s")

    if passed == total:
        print("\n🎉 ALL CHECKS PASSED! Code quality is excellent.")
        return 0
    print(f"\n⚠️  {total - passed} checks failed. Please review and fix issues.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
