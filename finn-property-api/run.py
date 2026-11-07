import json
import os
import sys
from pathlib import Path


def configure(options):
    key = options.get("api_key", "")
    if not isinstance(key, str) or len(key) < 24:
        raise ValueError("Set api_key to a random secret of at least 24 characters in app Configuration")
    env = {"API_KEY": key, "DATA_DIR": "/data/diagnostics"}
    for option, variable in (("finn_permission_confirmed", "FINN_PERMISSION_CONFIRMED"), ("save_failure_html", "SAVE_FAILURE_HTML")):
        value = options.get(option, False)
        if not isinstance(value, bool):
            raise ValueError(option + " must be a boolean")
        env[variable] = str(value).lower()
    return env


def main():
    os.umask(0o077)
    try:
        options = json.loads(Path("/data/options.json").read_text())
        environment = configure(options)
    except (OSError, ValueError, AttributeError) as error:
        raise SystemExit("App configuration failed: " + str(error))
    directory = Path(environment["DATA_DIR"])
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chown(directory, 10001, 10001)
    os.chmod(directory, 0o700)
    os.environ.update(environment)
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"])


if __name__ == "__main__":
    main()
