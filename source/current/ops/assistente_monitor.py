#!/usr/bin/env python3
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

SITE_URL = os.environ.get("ASSISTENTE_SITE_URL", "https://trab.sivaldodavi.com.br").rstrip("/")
CONTAINER = os.environ.get("ASSISTENTE_CONTAINER", "site-assistente-academico")
DATABASE = os.environ.get("ASSISTENTE_DATABASE", "/opt/servidor/data/assistente-academico/assistente_v2.sqlite3")
STATE = os.environ.get("ASSISTENTE_MONITOR_STATE", "/var/lib/assistente-monitor/state.json")


def command(*args: str) -> tuple[str, int]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return type(error).__name__, 1
    return result.stdout.strip(), result.returncode


def checks() -> list[str]:
    issues = []
    try:
        request = Request(SITE_URL + "/healthz", method="GET")
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                issues.append("site_http")
    except (OSError, URLError):
        issues.append("site_http")

    health, code = command("docker", "inspect", "--format", "{{.State.Health.Status}}", CONTAINER)
    if code or health != "healthy":
        issues.append("container_health")

    try:
        connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True, timeout=3)
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            issues.append("database_integrity")
        connection.close()
    except (OSError, sqlite3.Error):
        issues.append("database")

    usage = shutil.disk_usage("/opt/servidor")
    if usage.free < 2 * 1024**3:
        issues.append("disk_low")
    return issues


def main() -> int:
    issues = checks()
    payload = {"ok": not issues, "issues": issues}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
