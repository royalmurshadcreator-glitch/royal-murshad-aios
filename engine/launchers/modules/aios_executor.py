"""
AIOS Executor - Track E2 (hardened)
Backward-compatible: existing callers of execute(cmd) still work.
Adds: dry_run mode, confirm_token for HIGH/CRITICAL risk,
and structured risk assessment.
"""
import subprocess
from aios_guard import check_command


def execute(cmd, dry_run=False, confirm_token=None, timeout=30):
    """
    Execute a shell command with risk assessment.

    Args:
        cmd            : The command string
        dry_run        : If True, return the command without running it
        confirm_token  : Required for HIGH/CRITICAL risk commands.
                         Must equal 'YES_I_AM_SURE' to proceed.
        timeout        : Seconds (default 30, max 120)

    Returns dict with:
        ok, stdout, stderr, risk, dry_run, error, requires_confirmation
    """
    # 1. Risk assessment
    assessment = check_command(cmd)
    risk = assessment.get("risk", "low")

    # 2. Block unsafe commands
    if not assessment.get("safe", False):
        return {
            "ok": False,
            "error": "blocked",
            "risk": risk,
            "reason": assessment.get("reason", "safety check failed")
        }

    # 3. High-risk confirmation gate
    if risk in ("high", "critical"):
        if confirm_token != "YES_I_AM_SURE":
            return {
                "ok": False,
                "error": "requires_confirmation",
                "risk": risk,
                "reason": "high-risk command requires confirm_token='YES_I_AM_SURE'"
            }

    # 4. Dry-run
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "risk": risk,
            "cmd": cmd,
            "message": "Command not executed (dry_run=True)"
        }

    # 5. Execute
    try:
        timeout = min(int(timeout), 120)
        res = subprocess.run(
            cmd,
            shell=True,  # Preserved for backward compat (AIOS uses complex commands)
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "ok": True,
            "risk": risk,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "returncode": res.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "risk": risk,
            "error": "timeout",
            "timeout_seconds": timeout
        }
    except Exception as e:
        return {
            "ok": False,
            "risk": risk,
            "error": str(e)
        }
