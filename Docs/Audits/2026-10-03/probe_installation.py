"""Exercise the installed CLI's instance exclusion and graceful stop/start."""
from __future__ import annotations

import json
import subprocess
import sys


def invoke(command, timeout=15):
    return subprocess.run([sys.executable, "-m", "codex_auto_continuer", command],
                          capture_output=True, text=True, encoding="utf-8", timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)


def main():
    import codex_auto_continuer
    assert "site-packages" in codex_auto_continuer.__file__
    running = invoke("status", 45)
    assert running.returncode == 0 and json.loads(running.stdout)["supervisorRunning"]
    already = invoke("start")
    assert already.returncode == 0 and "already running" in already.stdout
    competing = invoke("once")
    assert competing.returncode == 2 and "Another Codex Auto Continuer instance" in competing.stderr
    stopped = invoke("stop", 65)
    assert stopped.returncode == 0 and "Supervisor stopped" in stopped.stdout
    status = invoke("status", 45)
    assert status.returncode == 0 and not json.loads(status.stdout)["supervisorRunning"]
    print(json.dumps({"installedVersion": codex_auto_continuer.__version__,
                      "runningStatus": True, "idempotentStart": "passed",
                      "competingOnceExitCode": competing.returncode,
                      "gracefulStop": "passed", "stoppedStatus": True}, indent=2))


if __name__ == "__main__":
    main()
