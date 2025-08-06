#!/usr/bin/env python3
"""
Comprehensive test runner for MCP server tests.
Runs all integration, E2E, authentication, routing, and multi-user tests.
"""

import subprocess
import sys
import os
from pathlib import Path
import argparse
import time


def run_command(cmd, description, timeout=300):
    """Run a command with timeout and error handling."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")

    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent,
        )

        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"✅ PASSED ({duration:.2f}s)")
            if result.stdout:
                print("STDOUT:")
                print(result.stdout)
        else:
            print(f"❌ FAILED ({duration:.2f}s)")
            print("STDOUT:")
            print(result.stdout)
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0, result.stdout, result.stderr, duration

    except subprocess.TimeoutExpired:
        print(f"⏰ TIMEOUT after {timeout}s")
        return False, "", f"Test timed out after {timeout}s", timeout
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False, "", str(e), 0


def main():
    """Run comprehensive MCP server tests."""
    parser = argparse.ArgumentParser(description="Run MCP server tests")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument("--e2e", action="store_true", help="Run E2E tests only")
    parser.add_argument(
        "--auth", action="store_true", help="Run authentication tests only"
    )
    parser.add_argument(
        "--routing", action="store_true", help="Run tool routing tests only"
    )
    parser.add_argument(
        "--multiuser", action="store_true", help="Run multi-user tests only"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--timeout", type=int, default=300, help="Test timeout in seconds"
    )

    args = parser.parse_args()

    print("🍽️  MCP Server Test Suite")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Working Directory: {Path.cwd()}")
    print(f"Test Directory: {Path(__file__).parent}")

    # Base pytest command
    pytest_cmd = [sys.executable, "-m", "pytest"]
    if args.verbose:
        pytest_cmd.extend(["-v", "-s"])
    else:
        pytest_cmd.append("-v")

    # Environment setup for tests
    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(Path(__file__).parent.parent)

    if args.quick:
        test_env["SKIP_SLOW_TESTS"] = "1"

    # Define test suites
    test_suites = []

    if args.integration or (
        not any([args.e2e, args.auth, args.routing, args.multiuser])
    ):
        test_suites.append(
            (
                pytest_cmd + ["tests/test_mcp_unified_integration.py"],
                "Integration Tests - Unified MCP Server",
                test_env,
            )
        )

    if args.e2e or (
        not any([args.integration, args.auth, args.routing, args.multiuser])
    ):
        test_suites.append(
            (
                pytest_cmd + ["tests/test_mcp_e2e.py"],
                "End-to-End Tests - MCP Protocol",
                test_env,
            )
        )

    if args.auth or (
        not any([args.integration, args.e2e, args.routing, args.multiuser])
    ):
        test_suites.append(
            (
                pytest_cmd + ["tests/test_mcp_auth.py"],
                "Authentication & Token Tests",
                test_env,
            )
        )

    if args.routing or (
        not any([args.integration, args.e2e, args.auth, args.multiuser])
    ):
        test_suites.append(
            (
                pytest_cmd + ["tests/test_mcp_tool_routing.py"],
                "Tool Routing & Error Handling Tests",
                test_env,
            )
        )

    if args.multiuser or (
        not any([args.integration, args.e2e, args.auth, args.routing])
    ):
        test_suites.append(
            (
                pytest_cmd + ["tests/test_mcp_multiuser.py"],
                "Multi-User Isolation Tests",
                test_env,
            )
        )

    # Run test suites
    results = []
    total_start_time = time.time()

    for cmd, description, env in test_suites:
        # Update environment for this test
        cmd_env = env.copy()

        success, stdout, stderr, duration = run_command(cmd, description, args.timeout)
        results.append((description, success, duration, stdout, stderr))

    total_duration = time.time() - total_start_time

    # Print summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for _, success, _, _, _ in results if success)
    total = len(results)

    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Total Duration: {total_duration:.2f}s")

    for description, success, duration, stdout, stderr in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {description} ({duration:.2f}s)")

        if not success and not args.verbose:
            # Show error details for failed tests
            print(
                f"   Error: {stderr[:200]}..."
                if len(stderr) > 200
                else f"   Error: {stderr}"
            )

    # Run additional checks if all tests passed
    if passed == total:
        print(f"\n🎉 All tests passed! Running additional checks...")

        # Check test coverage
        coverage_cmd = [
            sys.executable,
            "-m",
            "pytest",
            "--cov=mcp_server_unified",
            "--cov=mcp_tool_router",
            "--cov=mcp_tools",
            "--cov-report=term-missing",
            "tests/",
        ]

        print(f"\n📈 Running coverage analysis...")
        success, stdout, stderr, duration = run_command(
            coverage_cmd, "Test Coverage Analysis", args.timeout
        )

        if success and "%" in stdout:
            # Extract coverage percentage
            lines = stdout.split("\n")
            for line in lines:
                if "TOTAL" in line and "%" in line:
                    print(f"📊 {line}")
                    break

    # Exit with appropriate code
    exit_code = 0 if passed == total else 1

    if exit_code == 0:
        print(f"\n🚀 All MCP server tests completed successfully!")
        print(f"💡 Ready for production deployment")
    else:
        print(
            f"\n⚠️  Some tests failed. Please review and fix issues before deployment."
        )

    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
