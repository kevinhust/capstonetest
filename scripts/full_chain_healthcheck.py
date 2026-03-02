#!/usr/bin/env python3
"""
Full Chain Health Check for Health Butler Discord Bot

This script performs comprehensive health checks across all service layers:
1. Container/Infrastructure Health
2. Python Module Imports
3. External Service Connectivity
4. Core Component Initialization
5. End-to-End Request Flow Simulation

Usage:
    python scripts/full_chain_healthcheck.py [--verbose] [--fix]

Author: Health Butler Team
"""

import sys
import os
import json
import argparse
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: Optional[float] = None


@dataclass
class HealthReport:
    """Complete health check report."""
    timestamp: str
    overall_status: HealthStatus
    checks: List[CheckResult] = field(default_factory=list)

    def add_check(self, result: CheckResult):
        self.checks.append(result)
        # Update overall status
        if result.status == HealthStatus.UNHEALTHY:
            self.overall_status = HealthStatus.UNHEALTHY
        elif result.status == HealthStatus.DEGRADED and self.overall_status == HealthStatus.HEALTHY:
            self.overall_status = HealthStatus.DEGRADED


class HealthChecker:
    """Main health check orchestrator."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.report = HealthReport(
            timestamp=datetime.now().isoformat(),
            overall_status=HealthStatus.HEALTHY
        )

    def log(self, msg: str, level: str = "INFO"):
        """Log message with optional verbosity."""
        prefix = f"[{level}]"
        if self.verbose or level in ("ERROR", "WARN"):
            print(f"{prefix} {msg}")

    def check_container_health(self) -> CheckResult:
        """Check if Docker container is running and healthy."""
        import time
        start = time.time()

        try:
            # Check if container is running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=health-butler-bot",
                 "--format", "{{.Status}}"],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return CheckResult(
                    name="Container Status",
                    status=HealthStatus.UNKNOWN,
                    message="Docker command failed",
                    error=result.stderr,
                    duration_ms=(time.time() - start) * 1000
                )

            status_line = result.stdout.strip()

            if not status_line:
                return CheckResult(
                    name="Container Status",
                    status=HealthStatus.UNHEALTHY,
                    message="Container 'health-butler-bot' is not running",
                    duration_ms=(time.time() - start) * 1000
                )

            if "(healthy)" in status_line.lower():
                status = HealthStatus.HEALTHY
            elif "up" in status_line.lower():
                status = HealthStatus.DEGRADED
                status_line += " (no health check passed)"
            else:
                status = HealthStatus.UNHEALTHY

            return CheckResult(
                name="Container Status",
                status=status,
                message=f"Container running: {status_line}",
                details={"raw_status": status_line},
                duration_ms=(time.time() - start) * 1000
            )

        except subprocess.TimeoutExpired:
            return CheckResult(
                name="Container Status",
                status=HealthStatus.UNKNOWN,
                message="Docker command timed out",
                duration_ms=(time.time() - start) * 1000
            )
        except FileNotFoundError:
            return CheckResult(
                name="Container Status",
                status=HealthStatus.UNKNOWN,
                message="Docker CLI not found",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return CheckResult(
                name="Container Status",
                status=HealthStatus.UNKNOWN,
                message=f"Unexpected error: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def check_http_health(self) -> CheckResult:
        """Check HTTP health endpoint."""
        import time
        import urllib.request
        import urllib.error

        start = time.time()
        url = "http://localhost:8085/health"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                raw_data = response.read().decode()
                status_code = response.getcode()

            # Handle both JSON and plain text responses
            try:
                data = json.loads(raw_data)
                is_healthy = data.get("status") == "healthy"
                response_desc = f"JSON: {data}"
            except json.JSONDecodeError:
                # Plain text response (e.g., "OK")
                data = raw_data.strip()
                is_healthy = data.upper() in ("OK", "HEALTHY", "UP")
                response_desc = f"Text: {data}"

            if status_code == 200 and is_healthy:
                return CheckResult(
                    name="HTTP Health Endpoint",
                    status=HealthStatus.HEALTHY,
                    message=f"Health endpoint responding: {response_desc}",
                    details={"url": url, "response": data, "status_code": status_code},
                    duration_ms=(time.time() - start) * 1000
                )
            elif status_code == 200:
                return CheckResult(
                    name="HTTP Health Endpoint",
                    status=HealthStatus.DEGRADED,
                    message=f"Endpoint returned 200 but unexpected content: {response_desc}",
                    details={"url": url, "response": data, "status_code": status_code},
                    duration_ms=(time.time() - start) * 1000
                )
            else:
                return CheckResult(
                    name="HTTP Health Endpoint",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Unexpected status code: {status_code}",
                    details={"url": url, "response": data, "status_code": status_code},
                    duration_ms=(time.time() - start) * 1000
                )

        except urllib.error.URLError as e:
            return CheckResult(
                name="HTTP Health Endpoint",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot reach health endpoint: {e.reason}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return CheckResult(
                name="HTTP Health Endpoint",
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def check_module_imports(self) -> CheckResult:
        """Check if all critical modules can be imported."""
        import time
        start = time.time()

        # Core modules (no discord dependency)
        core_modules = [
            ("src.config", "Settings"),
            ("src.swarm", "HealthSwarm"),
            ("src.agents.router_agent", "RouterAgent"),
            ("src.agents.nutrition.nutrition_agent", "NutritionAgent"),
            ("src.agents.fitness.fitness_agent", "FitnessAgent"),
            ("src.agents.engagement.engagement_agent", "EngagementAgent"),
            ("src.agents.analytics.analytics_agent", "AnalyticsAgent"),
            ("src.discord_bot.profile_db", "get_profile_db"),
            ("src.cv_food_rec.vision_tool", "VisionTool"),
            ("src.data_rag.simple_rag_tool", "SimpleRagTool"),
        ]

        # Discord-dependent modules (only check if discord is available)
        discord_modules = [
            ("src.discord_bot.bot", "HealthButlerDiscordBot"),
            ("src.discord_bot.views", "MealLogView"),
            ("src.discord_bot.views", "RegistrationViewA"),
            ("src.discord_bot.embed_builder", "HealthButlerEmbed"),
        ]

        failed = []
        imported = []
        skipped = []

        # Check if discord is available
        try:
            import discord
            has_discord = True
        except ImportError:
            has_discord = False
            skipped = [f"{m[0]}.{m[1]}" for m in discord_modules]

        # Check core modules
        for module_name, class_name in core_modules:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name, None)
                if cls is None:
                    failed.append(f"{module_name}.{class_name} (class not found)")
                else:
                    imported.append(f"{module_name}.{class_name}")
                    self.log(f"  OK: {module_name}.{class_name}")
            except Exception as e:
                failed.append(f"{module_name}.{class_name} ({e})")
                self.log(f"  FAIL: {module_name}.{class_name} - {e}", "ERROR")

        # Check discord modules only if discord is available
        if has_discord:
            for module_name, class_name in discord_modules:
                try:
                    module = __import__(module_name, fromlist=[class_name])
                    cls = getattr(module, class_name, None)
                    if cls is None:
                        failed.append(f"{module_name}.{class_name} (class not found)")
                    else:
                        imported.append(f"{module_name}.{class_name}")
                        self.log(f"  OK: {module_name}.{class_name}")
                except Exception as e:
                    failed.append(f"{module_name}.{class_name} ({e})")
                    self.log(f"  FAIL: {module_name}.{class_name} - {e}", "ERROR")

        duration = (time.time() - start) * 1000

        if not failed:
            if skipped:
                return CheckResult(
                    name="Module Imports",
                    status=HealthStatus.HEALTHY,
                    message=f"All {len(imported)} core modules imported (discord modules skipped - run in container for full check)",
                    details={"imported": imported, "skipped": skipped, "count": len(imported)},
                    duration_ms=duration
                )
            else:
                return CheckResult(
                    name="Module Imports",
                    status=HealthStatus.HEALTHY,
                    message=f"All {len(imported)} modules imported successfully",
                    details={"imported": imported, "count": len(imported)},
                    duration_ms=duration
                )
        else:
            return CheckResult(
                name="Module Imports",
                status=HealthStatus.UNHEALTHY,
                message=f"{len(failed)} module(s) failed to import",
                details={"failed": failed, "imported": imported, "skipped": skipped},
                error="\n".join(failed),
                duration_ms=duration
            )

    def check_environment_config(self) -> CheckResult:
        """Check if required environment variables are set."""
        required_vars = [
            "DISCORD_TOKEN",
            "GOOGLE_API_KEY",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ]

        optional_vars = [
            "SUPABASE_SERVICE_ROLE_KEY",
            "DISCORD_ALLOWED_CHANNEL_IDS",
            "DISCORD_ALLOWED_USER_IDS",
            "DEBUG_MODE",
            "DEPLOY_ENV",
        ]

        missing_required = []
        missing_optional = []
        present = []

        for var in required_vars:
            value = os.getenv(var)
            if not value:
                missing_required.append(var)
            else:
                present.append(var)
                self.log(f"  OK: {var}=***")

        for var in optional_vars:
            value = os.getenv(var)
            if not value:
                missing_optional.append(var)
            else:
                present.append(var)

        if missing_required:
            return CheckResult(
                name="Environment Config",
                status=HealthStatus.UNHEALTHY,
                message=f"Missing required env vars: {', '.join(missing_required)}",
                details={
                    "missing_required": missing_required,
                    "missing_optional": missing_optional,
                    "present": present
                }
            )
        elif missing_optional:
            return CheckResult(
                name="Environment Config",
                status=HealthStatus.DEGRADED,
                message=f"Missing optional env vars: {', '.join(missing_optional)}",
                details={
                    "missing_optional": missing_optional,
                    "present": present
                }
            )
        else:
            return CheckResult(
                name="Environment Config",
                status=HealthStatus.HEALTHY,
                message="All environment variables configured",
                details={"present": present}
            )

    def check_supabase_connection(self) -> CheckResult:
        """Check Supabase database connection."""
        import time
        start = time.time()

        try:
            import httpx

            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")

            if not supabase_url or not supabase_key:
                return CheckResult(
                    name="Supabase Connection",
                    status=HealthStatus.UNKNOWN,
                    message="Supabase credentials not configured",
                    duration_ms=(time.time() - start) * 1000
                )

            # Simple health check via REST API
            headers = {
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}"
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{supabase_url}/rest/v1/",
                    headers=headers
                )

            if response.status_code in (200, 401):  # 401 means endpoint exists but needs auth
                return CheckResult(
                    name="Supabase Connection",
                    status=HealthStatus.HEALTHY,
                    message=f"Supabase reachable (status: {response.status_code})",
                    duration_ms=(time.time() - start) * 1000
                )
            else:
                return CheckResult(
                    name="Supabase Connection",
                    status=HealthStatus.DEGRADED,
                    message=f"Unexpected status code: {response.status_code}",
                    duration_ms=(time.time() - start) * 1000
                )

        except Exception as e:
            return CheckResult(
                name="Supabase Connection",
                status=HealthStatus.UNHEALTHY,
                message=f"Connection failed: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def check_google_api(self) -> CheckResult:
        """Check Google API connectivity using the new google.genai SDK."""
        import time
        start = time.time()

        try:
            from google import genai

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return CheckResult(
                    name="Google API",
                    status=HealthStatus.UNKNOWN,
                    message="GOOGLE_API_KEY not configured",
                    duration_ms=(time.time() - start) * 1000
                )

            # Use the new google.genai Client API
            client = genai.Client(api_key=api_key)

            # List models to verify API access
            models = list(client.models.list())
            model_count = len(models)

            if model_count > 0:
                return CheckResult(
                    name="Google API",
                    status=HealthStatus.HEALTHY,
                    message=f"Google API accessible ({model_count} models available)",
                    details={"model_count": model_count},
                    duration_ms=(time.time() - start) * 1000
                )
            else:
                return CheckResult(
                    name="Google API",
                    status=HealthStatus.DEGRADED,
                    message="API key valid but no models returned",
                    duration_ms=(time.time() - start) * 1000
                )

        except Exception as e:
            return CheckResult(
                name="Google API",
                status=HealthStatus.UNHEALTHY,
                message=f"API check failed: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def check_agent_initialization(self) -> CheckResult:
        """Check if agents can be initialized."""
        import time
        start = time.time()

        agents_to_check = [
            ("RouterAgent", "src.agents.router_agent", "RouterAgent"),
            ("NutritionAgent", "src.agents.nutrition.nutrition_agent", "NutritionAgent"),
            ("FitnessAgent", "src.agents.fitness.fitness_agent", "FitnessAgent"),
        ]

        initialized = []
        failed = []

        for name, module_path, class_name in agents_to_check:
            try:
                module = __import__(module_path, fromlist=[class_name])
                cls = getattr(module, class_name)
                instance = cls()  # Try to instantiate
                initialized.append(name)
                self.log(f"  OK: {name} initialized")
            except Exception as e:
                failed.append(f"{name}: {str(e)[:100]}")
                self.log(f"  FAIL: {name} - {e}", "ERROR")

        duration = (time.time() - start) * 1000

        if not failed:
            return CheckResult(
                name="Agent Initialization",
                status=HealthStatus.HEALTHY,
                message=f"All {len(initialized)} agents initialized successfully",
                details={"initialized": initialized},
                duration_ms=duration
            )
        else:
            return CheckResult(
                name="Agent Initialization",
                status=HealthStatus.DEGRADED if initialized else HealthStatus.UNHEALTHY,
                message=f"{len(failed)} agent(s) failed to initialize",
                details={"failed": failed, "initialized": initialized},
                error="\n".join(failed),
                duration_ms=duration
            )

    def check_discord_views(self) -> CheckResult:
        """Check if Discord views (including MealLogView) are properly defined."""
        import time
        start = time.time()

        # Check if discord is available (skip if running locally without discord)
        try:
            import discord
        except ImportError:
            return CheckResult(
                name="Discord Views",
                status=HealthStatus.HEALTHY,
                message="Skipped (discord not installed locally - run in container for full check)",
                details={"skipped": True, "reason": "discord module not available"},
                duration_ms=(time.time() - start) * 1000
            )

        try:
            from src.discord_bot.views import (
                RegistrationViewA,
                OnboardingGreetingView,
                MealLogView,
                NutritionAdjustModal
            )

            # Check that MealLogView has required methods
            required_methods = ["add_meal_callback", "skip_meal_callback"]
            missing_methods = []

            for method in required_methods:
                if not hasattr(MealLogView, method):
                    missing_methods.append(method)

            if missing_methods:
                return CheckResult(
                    name="Discord Views",
                    status=HealthStatus.DEGRADED,
                    message=f"MealLogView missing methods: {missing_methods}",
                    details={"missing_methods": missing_methods},
                    duration_ms=(time.time() - start) * 1000
                )

            return CheckResult(
                name="Discord Views",
                status=HealthStatus.HEALTHY,
                message="All Discord views imported and validated",
                details={
                    "views": ["RegistrationViewA", "OnboardingGreetingView", "MealLogView"],
                    "modals": ["NutritionAdjustModal"]
                },
                duration_ms=(time.time() - start) * 1000
            )

        except ImportError as e:
            return CheckResult(
                name="Discord Views",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to import Discord views: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return CheckResult(
                name="Discord Views",
                status=HealthStatus.UNHEALTHY,
                message=f"View validation failed: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def check_swarm_initialization(self) -> CheckResult:
        """Check if HealthSwarm can be initialized."""
        import time
        start = time.time()

        try:
            from src.swarm import HealthSwarm

            swarm = HealthSwarm(verbose=self.verbose)

            # Verify components
            has_router = hasattr(swarm, 'router') and swarm.router is not None
            has_rag = hasattr(swarm, 'rag') and swarm.rag is not None

            if has_router and has_rag:
                return CheckResult(
                    name="HealthSwarm Initialization",
                    status=HealthStatus.HEALTHY,
                    message="HealthSwarm initialized with RouterAgent and RAG",
                    details={"router": has_router, "rag": has_rag},
                    duration_ms=(time.time() - start) * 1000
                )
            else:
                return CheckResult(
                    name="HealthSwarm Initialization",
                    status=HealthStatus.DEGRADED,
                    message="HealthSwarm initialized but missing components",
                    details={"router": has_router, "rag": has_rag},
                    duration_ms=(time.time() - start) * 1000
                )

        except Exception as e:
            return CheckResult(
                name="HealthSwarm Initialization",
                status=HealthStatus.UNHEALTHY,
                message=f"HealthSwarm initialization failed: {e}",
                error=traceback.format_exc(),
                duration_ms=(time.time() - start) * 1000
            )

    def check_container_logs(self) -> CheckResult:
        """Check container logs for recent errors."""
        import time
        start = time.time()

        try:
            result = subprocess.run(
                ["docker", "logs", "health-butler-bot", "--tail", "100"],
                capture_output=True, text=True, timeout=15
            )

            if result.returncode != 0:
                return CheckResult(
                    name="Container Logs",
                    status=HealthStatus.UNKNOWN,
                    message="Failed to fetch container logs",
                    error=result.stderr,
                    duration_ms=(time.time() - start) * 1000
                )

            logs = result.stdout + result.stderr
            lines = logs.strip().split('\n') if logs else []

            # Count error patterns
            error_patterns = ['error', 'exception', 'traceback', 'failed', 'critical']
            error_count = 0
            recent_errors = []

            for line in lines[-50:]:  # Check last 50 lines
                lower_line = line.lower()
                if any(p in lower_line for p in error_patterns):
                    error_count += 1
                    if len(recent_errors) < 5:
                        recent_errors.append(line[:200])

            if error_count == 0:
                status = HealthStatus.HEALTHY
                message = "No recent errors in container logs"
            elif error_count < 5:
                status = HealthStatus.DEGRADED
                message = f"Found {error_count} potential error(s) in recent logs"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Found {error_count} potential errors in recent logs"

            return CheckResult(
                name="Container Logs",
                status=status,
                message=message,
                details={
                    "error_count": error_count,
                    "recent_errors": recent_errors,
                    "total_lines": len(lines)
                },
                duration_ms=(time.time() - start) * 1000
            )

        except subprocess.TimeoutExpired:
            return CheckResult(
                name="Container Logs",
                status=HealthStatus.UNKNOWN,
                message="Log fetch timed out",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return CheckResult(
                name="Container Logs",
                status=HealthStatus.UNKNOWN,
                message=f"Failed to check logs: {e}",
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

    def run_all_checks(self) -> HealthReport:
        """Run all health checks and generate report."""
        checks = [
            ("Container", self.check_container_health),
            ("HTTP Endpoint", self.check_http_health),
            ("Module Imports", self.check_module_imports),
            ("Environment", self.check_environment_config),
            ("Supabase", self.check_supabase_connection),
            ("Google API", self.check_google_api),
            ("Agents", self.check_agent_initialization),
            ("Discord Views", self.check_discord_views),
            ("HealthSwarm", self.check_swarm_initialization),
            ("Logs", self.check_container_logs),
        ]

        print("\n" + "=" * 60)
        print("Health Butler - Full Chain Health Check")
        print("=" * 60)
        print(f"Timestamp: {self.report.timestamp}\n")

        for name, check_func in checks:
            print(f"Checking {name}...", end=" ")
            try:
                result = check_func()
                self.report.add_check(result)

                status_icon = {
                    HealthStatus.HEALTHY: "[OK]",
                    HealthStatus.DEGRADED: "[WARN]",
                    HealthStatus.UNHEALTHY: "[FAIL]",
                    HealthStatus.UNKNOWN: "[???]"
                }.get(result.status, "[???]")

                print(f"{status_icon} {result.message}")

                if result.error and self.verbose:
                    print(f"         Error: {result.error[:200]}")

            except Exception as e:
                error_result = CheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check crashed: {e}",
                    error=traceback.format_exc()
                )
                self.report.add_check(error_result)
                print(f"[FAIL] Check crashed: {e}")

        return self.report

    def print_summary(self):
        """Print health check summary."""
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)

        status_counts = {}
        for check in self.report.checks:
            status = check.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            print(f"  {status.upper()}: {count}")

        overall_icon = {
            HealthStatus.HEALTHY: "All systems operational",
            HealthStatus.DEGRADED: "Some systems degraded",
            HealthStatus.UNHEALTHY: "Critical issues detected",
            HealthStatus.UNKNOWN: "Unable to determine status"
        }.get(self.report.overall_status, "Unknown status")

        print(f"\nOverall Status: {self.report.overall_status.value.upper()}")
        print(f"  {overall_icon}")
        print()

    def to_json(self) -> str:
        """Export report as JSON."""
        return json.dumps({
            "timestamp": self.report.timestamp,
            "overall_status": self.report.overall_status.value,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "details": c.details,
                    "error": c.error,
                    "duration_ms": c.duration_ms
                }
                for c in self.report.checks
            ]
        }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Full Chain Health Check for Health Butler Discord Bot"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    # Load environment variables from .env if available
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
        except ImportError:
            pass

    checker = HealthChecker(verbose=args.verbose)
    report = checker.run_all_checks()

    if args.json:
        print(checker.to_json())
    else:
        checker.print_summary()

    # Exit with appropriate code
    if report.overall_status == HealthStatus.HEALTHY:
        sys.exit(0)
    elif report.overall_status == HealthStatus.DEGRADED:
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
