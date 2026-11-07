import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from settings import enabled, settings


def prepare_x11_directory(path=Path("/tmp/.X11-unix")):
    if path.is_symlink():
        raise RuntimeError("Refusing a symlink as X11 socket directory")
    path.mkdir(parents=True, exist_ok=True)
    os.chown(path, 0, 0)
    path.chmod(0o1777)


def main():
    os.umask(0o077)
    options_file = Path("/data/options.json")
    if options_file.exists():
        options = json.loads(options_file.read_text())
    else:
        options = {"api_key": os.getenv("API_KEY", "")}
        for option, variable, default in (("finn_permission_confirmed", "FINN_PERMISSION_CONFIRMED", "false"), ("save_failure_html", "SAVE_FAILURE_HTML", "false"), ("browser_setup_enabled", "BROWSER_SETUP_ENABLED", "false"), ("chromium_sandbox", "CHROMIUM_SANDBOX", "true")):
            options[option] = os.getenv(variable, default).lower() == "true"
    try:
        os.environ.update(settings(options))
    except (ValueError, AttributeError) as exc:
        raise SystemExit(str(exc))
    prepare_x11_directory()
    for folder in ("/data/diagnostics", "/data/browser-profile", "/tmp/finn-runtime"):
        path = Path(folder)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chown(path, 10001, 10001)
        os.chmod(path, 0o700)
    os.environ.update(DISPLAY=":99", HOME="/home/api", XDG_RUNTIME_DIR="/tmp/finn-runtime")
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)
    template = Path("/app/nginx.conf").read_text()
    location = "root /usr/share/novnc; index setup.html;" if enabled("BROWSER_SETUP_ENABLED") else 'return 200 "Browser setup is disabled. Enable browser_setup_enabled and restart the app.";'
    Path("/tmp/finn-nginx.conf").write_text(template.replace("__SETUP_LOCATION__", location))
    subprocess.run(["nginx", "-t", "-c", "/tmp/finn-nginx.conf"], check=True)
    children = []
    api = None
    stopping = False
    def stop(signum, frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    def start(args):
        process = subprocess.Popen(args, start_new_session=True)
        children.append(process)
        return process
    try:
        display = start(["Xvfb", ":99", "-screen", "0", "1280x900x24", "-nolisten", "tcp"])
        for _ in range(100):
            if Path("/tmp/.X11-unix/X99").exists():
                break
            if display.poll() is not None:
                raise RuntimeError("Xvfb exited with code " + str(display.returncode))
            time.sleep(0.1)
        else:
            raise RuntimeError("Xvfb did not start")
        if enabled("BROWSER_SETUP_ENABLED"):
            start(["x11vnc", "-display", ":99", "-localhost", "-rfbport", "5900", "-nopw", "-forever", "-shared", "-noxdamage", "-quiet"])
            start(["/usr/bin/websockify", "127.0.0.1:6080", "127.0.0.1:5900"])
        start(["nginx", "-c", "/tmp/finn-nginx.conf", "-g", "daemon off;"])
        api = start([sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"])
        while not stopping:
            for process in children:
                if process.poll() is not None:
                    raise RuntimeError("Required process exited: " + str(process.args[0]) + " (code " + str(process.returncode) + "); inspect preceding logs")
            time.sleep(0.5)
    finally:
        if api and api.poll() is None:
            api.terminate()
            try:
                api.wait(timeout=45)
            except subprocess.TimeoutExpired:
                pass
        for process in reversed(children):
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for process in children:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    main()
