"""Fail-closed Python execution. User code runs only inside a Docker container.

The container has no network, a read-only root filesystem, one read-only source mount,
resource limits, no Linux capabilities and an unprivileged UID. If Docker is unavailable,
we return a clear setup message rather than executing source in the API process.
"""
from __future__ import annotations
import os, shutil, subprocess, tempfile, time
from pathlib import Path

MAX_OUTPUT = 20_000
IMAGE = os.getenv("SQ_PYTHON_IMAGE", "python:3.13-alpine")
TIMEOUT = int(os.getenv("SQ_RUN_TIMEOUT", "5"))

def isolation_level() -> str:
    if not shutil.which("docker"):
        return "disabled — Docker is not installed; user code is not executed"
    try:
        r = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=3)
        if r.returncode != 0:
            return "disabled — Docker daemon is unavailable; user code is not executed"
        return "Docker: network disabled, read-only root, 128 MB memory, 0.5 CPU, 32 process limit"
    except Exception:
        return "disabled — Docker daemon is unavailable; user code is not executed"

def run_python(source: str, stdin: str = "") -> dict:
    start = time.monotonic()
    if len(source) > 20_000:
        return _result("", "Code is too large (20,000 character limit).", 1, start, "InputLimitError")
    if len(stdin) > 5_000:
        return _result("", "Input is too large (5,000 character limit).", 1, start, "InputLimitError")
    if not shutil.which("docker"):
        return _result("", "Safe runner unavailable: install Docker Desktop, start it, and pull the image with `docker pull python:3.13-alpine`. No code was executed.", 1, start, "SandboxUnavailable")
    info = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=4)
    if info.returncode:
        return _result("", "Safe runner unavailable: Docker is installed but its engine is not running. Start Docker Desktop and try again. No code was executed.", 1, start, "SandboxUnavailable")
    with tempfile.TemporaryDirectory(prefix="sq-run-") as temp:
        work = Path(temp)
        script = work / "main.py"
        script.write_text(source, encoding="utf-8")
        try:
            os.chmod(work, 0o755)
            os.chmod(script, 0o444)
            cmd = [
                "docker", "run", "--rm", "--pull=never", "--network=none",
                "--memory=128m", "--memory-swap=128m", "--cpus=0.5", "--pids-limit=32",
                "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges",
                "--user=65534:65534", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--mount", f"type=bind,src={work},dst=/workspace,readonly",
                "--workdir=/workspace", IMAGE, "python", "-I", "-B", "/workspace/main.py",
            ]
            p = subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                               timeout=TIMEOUT + 3, errors="replace")
            out = (p.stdout or "")[:MAX_OUTPUT]
            err = (p.stderr or "")[:MAX_OUTPUT]
            if "Unable to find image" in err or "No such image" in err:
                return _result("", f"Sandbox image is missing. Run `docker pull {IMAGE}` and retry. No code was executed.", 1, start, "SandboxImageMissing")
            typ = None
            if p.returncode:
                typ = "ExecutionError"
                if "SyntaxError" in err: typ = "SyntaxError"
                elif "IndentationError" in err: typ = "IndentationError"
                elif "NameError" in err: typ = "NameError"
                elif "TypeError" in err: typ = "TypeError"
                elif "ValueError" in err: typ = "ValueError"
                elif "ZeroDivisionError" in err: typ = "ZeroDivisionError"
            return _result(out, err, p.returncode, start, typ)
        except subprocess.TimeoutExpired:
            return _result("", f"Time limit reached ({TIMEOUT} seconds). Check for an infinite loop.", 124, start, "TimeoutError", timed_out=True)
        except Exception as exc:
            return _result("", f"Sandbox could not start: {type(exc).__name__}. No code was executed.", 1, start, "SandboxError")

def _result(stdout: str, stderr: str, exit_code: int, started: float, error_type: str | None, timed_out: bool = False) -> dict:
    hints = {
        "SyntaxError": "Python could not read this line. Check colons, brackets, quotes and = versus ==.",
        "IndentationError": "Indentation must be consistent inside blocks. Use four spaces.",
        "NameError": "A name is used before it is defined, or it is misspelt.",
        "TypeError": "An operation received a value of the wrong type. Check conversions such as int() or str().",
        "ValueError": "The value has the right type but unsuitable content. Check the input value.",
        "ZeroDivisionError": "A number is being divided by zero. Check the divisor.",
        "TimeoutError": "The program ran for too long. Check loops and recursion.",
        "SandboxUnavailable": "Start Docker and pull the configured Python image. The app will not run code without isolation.",
    }
    err = None if not error_type else {"type": error_type, "message": (stderr.strip().splitlines()[-1] if stderr.strip() else error_type), "line": None, "explanation": hints.get(error_type, "Read the error message and inspect the line where it occurs.")}
    return {"stdout": stdout, "stderr": stderr, "exit": exit_code, "ms": round((time.monotonic() - started) * 1000), "timed_out": timed_out, "error": err, "sandbox": isolation_level()}
