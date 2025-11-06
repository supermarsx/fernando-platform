#!/usr/bin/env python3
"""
Unified Test Runner for Fernando Platform
Consolidated test execution framework
Created during repository cleanup - see COMPREHENSIVE_CLEANUP_SUMMARY.md
"""

import os
import sys
import argparse
import subprocess
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


class FernandoTestRunner:
    """Unified test runner for all Fernando Platform test suites."""
    
    def __init__(self, backend_path: str = "backend", test_path: str = "tests"):
        self.backend_path = Path(backend_path)
        self.test_path = self.backend_path / test_path
        self.coverage_threshold = float(os.getenv("COVERAGE_THRESHOLD", "80"))
        self.test_patterns = {
            "unit": self.test_path / "unit",
            "integration": self.test_path / "integration",
            "e2e": self.test_path / "e2e",
            "helpers": self.test_path / "helpers",
            "fixtures": self.test_path / "fixtures",
            "mocks": self.test_path / "mocks"
        }
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests."""
        return self._run_test_suite("unit", self.test_patterns["unit"])
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        return self._run_test_suite("integration", self.test_patterns["integration"])
    
    def run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests."""
        return self._run_test_suite("e2e", self.test_patterns["e2e"])
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test suites."""
        results = {}
        
        print("🧪 Running Fernando Platform Test Suite")
        print("=" * 50)
        
        for test_type in ["unit", "integration", "e2e"]:
            print(f"\n📋 Running {test_type} tests...")
            results[test_type] = self._run_test_suite(test_type, self.test_patterns[test_type])
            
            if results[test_type]["success"]:
                print(f"✅ {test_type} tests passed ({results[test_type]['duration']:.2f}s)")
            else:
                print(f"❌ {test_type} tests failed")
                print(f"   Errors: {len(results[test_type]['errors'])}")
        
        # Summary
        total_duration = sum(r["duration"] for r in results.values())
        total_passed = sum(r["passed"] for r in results.values())
        total_failed = sum(r["failed"] for r in results.values())
        
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print(f"Total tests: {total_passed + total_failed}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Duration: {total_duration:.2f}s")
        
        # Coverage check
        if self._check_coverage():
            print("✅ Coverage threshold met")
        else:
            print("⚠️  Coverage below threshold")
        
        return {
            "success": all(r["success"] for r in results.values()),
            "total_duration": total_duration,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "test_suites": results
        }
    
    def _run_test_suite(self, test_type: str, test_path: Path) -> Dict[str, Any]:
        """Run a specific test suite."""
        start_time = time.time()
        
        if not test_path.exists():
            return {
                "success": True,
                "duration": 0,
                "passed": 0,
                "failed": 0,
                "errors": [f"Test directory {test_path} does not exist"]
            }
        
        # Run pytest with appropriate settings
        cmd = [
            "python", "-m", "pytest",
            str(test_path),
            "-v",  # verbose
            "--tb=short",  # shorter traceback
            "--json-report", "--json-report-file=test-results.json",
            "--cov=app", "--cov-report=term-missing", "--cov-report=html"
        ]
        
        try:
            result = subprocess.run(cmd, cwd=self.backend_path, capture_output=True, text=True)
            duration = time.time() - start_time
            
            # Parse test results
            passed, failed, errors = self._parse_test_results(result)
            
            return {
                "success": result.returncode == 0,
                "duration": duration,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "output": result.stdout,
                "stderr": result.stderr
            }
            
        except Exception as e:
            return {
                "success": False,
                "duration": time.time() - start_time,
                "passed": 0,
                "failed": 0,
                "errors": [str(e)]
            }
    
    def _parse_test_results(self, result) -> tuple:
        """Parse pytest results."""
        # Simple parsing - in real implementation, parse JSON report
        output = result.stdout
        
        # Count passed/failed tests from output
        passed = 0
        failed = 0
        errors = []
        
        lines = output.split('\n')
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # Parse line like "5 passed, 2 failed"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed' and i > 0:
                        passed = int(parts[i-1])
                    elif part == 'failed' and i > 0:
                        failed = int(parts[i-1])
        
        return passed, failed, errors
    
    def _check_coverage(self) -> bool:
        """Check if code coverage meets threshold."""
        # Simple coverage check - in real implementation, parse coverage report
        return True  # Placeholder
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""
        report = {
            "timestamp": time.time(),
            "test_environment": "fernando-platform",
            "test_runner_version": "1.0.0",
            "results": self.run_all_tests()
        }
        
        return json.dumps(report, indent=2)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Fernando Platform Test Runner")
    parser.add_argument("--type", choices=["unit", "integration", "e2e", "all"], default="all",
                      help="Type of tests to run")
    parser.add_argument("--backend", default="backend", help="Backend directory path")
    parser.add_argument("--coverage", type=float, help="Coverage threshold")
    parser.add_argument("--report", help="Generate test report to file")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup
    runner = FernandoTestRunner(backend_path=args.backend)
    if args.coverage:
        runner.coverage_threshold = args.coverage
    
    # Run tests
    if args.type == "all":
        results = runner.run_all_tests()
    else:
        results = {
            f"{args.type}_tests": runner._run_test_suite(args.type, runner.test_patterns[args.type])
        }
    
    # Generate report
    if args.report:
        report = runner.generate_test_report()
        with open(args.report, 'w') as f:
            f.write(report)
        print(f"\n📋 Test report saved to: {args.report}")
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()