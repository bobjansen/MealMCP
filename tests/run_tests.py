#!/usr/bin/env python3
"""
Test runner for MealMCP server tests.
Provides easy access to all test suites.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_direct_tests():
    """Run direct function tests."""
    print("🧪 Running Direct Function Tests")
    print("=" * 40)
    subprocess.run([
        sys.executable, 
        str(Path(__file__).parent / "mcp_tests" / "test_direct_functions.py")
    ], cwd=project_root)

def run_scenario_tests():
    """Run end-to-end scenario tests."""
    print("\n🎭 Running Scenario Tests")
    print("=" * 40)
    subprocess.run([
        sys.executable,
        str(Path(__file__).parent / "mcp_tests" / "test_scenarios.py")
    ], cwd=project_root)

def run_interactive_tests():
    """Run interactive tests."""
    print("\n🎮 Running Interactive Tests")
    print("=" * 40)
    subprocess.run([
        sys.executable,
        str(Path(__file__).parent / "mcp_tests" / "test_interactive.py"),
        "interactive"
    ], cwd=project_root)

def run_quick_tests():
    """Run quick automated tests."""
    print("\n⚡ Running Quick Tests")
    print("=" * 40)
    subprocess.run([
        sys.executable,
        str(Path(__file__).parent / "mcp_tests" / "test_interactive.py"),
        "quick"
    ], cwd=project_root)

def run_pytest():
    """Run pytest unit tests."""
    print("\n🔬 Running Unit Tests (pytest)")
    print("=" * 40)
    subprocess.run(["uv", "run", "pytest", "tests/", "-v"], cwd=project_root)

def show_help():
    """Show available test commands."""
    print("🧪 MealMCP Test Runner")
    print("=" * 30)
    print("Available commands:")
    print("  direct      - Run direct function tests")
    print("  scenarios   - Run end-to-end scenario tests")
    print("  interactive - Run interactive test menu")
    print("  quick       - Run quick automated tests")
    print("  pytest      - Run pytest unit tests")
    print("  all         - Run all automated tests")
    print("  help        - Show this help message")
    print("\nUsage:")
    print("  python tests/run_tests.py <command>")
    print("  uv run python tests/run_tests.py <command>")

def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "direct":
        run_direct_tests()
    elif command == "scenarios":
        run_scenario_tests()
    elif command == "interactive":
        run_interactive_tests()
    elif command == "quick":
        run_quick_tests()
    elif command == "pytest":
        run_pytest()
    elif command == "all":
        run_direct_tests()
        run_scenario_tests()
        run_quick_tests()
        run_pytest()
    elif command == "help":
        show_help()
    else:
        print(f"Unknown command: {command}")
        show_help()

if __name__ == "__main__":
    main()