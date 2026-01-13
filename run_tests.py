#!/usr/bin/env python3
"""
Helper script to run tests with optional coverage reporting and parallel execution.

Usage:
    python run_tests.py              # Run tests in parallel (auto-detected workers)
    python run_tests.py --coverage   # Run tests with coverage
    python run_tests.py -c           # Short form for coverage
    python run_tests.py --cov        # Alternative coverage flag
    python run_tests.py --html       # Generate HTML coverage report
    python run_tests.py -v           # Verbose output
    python run_tests.py -n 4         # Run with 4 parallel workers
    python run_tests.py -n 1         # Run sequentially (no parallel)
    python run_tests.py --help       # Show help
"""

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Run the test suite with optional coverage reporting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                           # Run tests in parallel (auto workers)
  python run_tests.py -n 4                      # Run tests with 4 parallel workers
  python run_tests.py -n 1                      # Run tests sequentially
  python run_tests.py --coverage                # Run with terminal coverage report
  python run_tests.py --html                    # Run with HTML coverage report
  python run_tests.py --coverage --html         # Run with both reports
  python run_tests.py -v                        # Verbose test output
  python run_tests.py tests/test_fit_editor.py  # Run specific test file
  python run_tests.py -v -n 2 --coverage        # Verbose, 2 workers, with coverage
        """,
    )

    parser.add_argument(
        "-c",
        "--coverage",
        "--cov",
        action="store_true",
        help="Generate coverage report (terminal output)",
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML coverage report (implies --coverage)",
    )

    parser.add_argument(
        "--xml",
        action="store_true",
        help="Generate XML coverage report (implies --coverage)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Verbose test output"
    )

    parser.add_argument(
        "--no-cov-on-fail",
        action="store_true",
        help="Don't show coverage report if tests fail",
    )

    parser.add_argument(
        "-n",
        "--workers",
        nargs="?",
        const="auto",
        type=str,
        help="Run tests in parallel with specified number of workers (default: auto). Use -n 1 to disable parallelization",
    )

    parser.add_argument(
        "pytest_args", nargs="*", help="Additional arguments to pass to pytest"
    )

    args = parser.parse_args()

    # Build pytest command
    cmd = ["uv", "run", "pytest"]

    # Add test path (default to tests/)
    if args.pytest_args:
        cmd.extend(args.pytest_args)
    else:
        cmd.append("tests/")

    # Add parallel execution (default to auto)
    workers = args.workers if args.workers is not None else "auto"
    if workers != "1":
        cmd.extend(["-n", workers])

    # Add verbose flag
    if args.verbose and "-v" not in args.pytest_args:
        cmd.append("-v")

    # Add coverage options
    if args.coverage or args.html or args.xml:
        cmd.extend(["--cov=fit_file_faker"])

        # Add coverage report formats
        if args.coverage or (not args.html and not args.xml):
            # Default to term-missing if coverage requested but no specific format
            cmd.append("--cov-report=term-missing")

        if args.html:
            cmd.append("--cov-report=html")

        if args.xml:
            cmd.append("--cov-report=xml")

        if args.no_cov_on_fail:
            cmd.append("--no-cov-on-fail")

    # Print command
    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    # Run pytest
    result = subprocess.run(cmd)

    # If HTML report was generated, print instructions
    if args.html and result.returncode == 0:
        html_path = Path("htmlcov/index.html")
        if html_path.exists():
            print("\n" + "=" * 60)
            print("HTML coverage report generated!")
            print(f"Open: {html_path.absolute()}")
            print("\nTo view:")
            if sys.platform == "darwin":
                print("  open htmlcov/index.html")
            elif sys.platform == "win32":
                print("  start htmlcov/index.html")
            else:
                print("  xdg-open htmlcov/index.html")
            print("=" * 60)

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
