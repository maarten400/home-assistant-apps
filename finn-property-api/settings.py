import os


def settings(options):
    key = options.get("api_key", "")
    if not isinstance(key, str) or len(key) < 24:
        raise ValueError("api_key must be a random secret of at least 24 characters")
    result = {"API_KEY": key, "DATA_DIR": "/data/diagnostics", "BROWSER_PROFILE_DIR": "/data/browser-profile"}
    for option, variable, default in (
        ("finn_permission_confirmed", "FINN_PERMISSION_CONFIRMED", False),
        ("save_failure_html", "SAVE_FAILURE_HTML", False),
        ("browser_setup_enabled", "BROWSER_SETUP_ENABLED", False),
        ("chromium_sandbox", "CHROMIUM_SANDBOX", True),
    ):
        value = options.get(option, default)
        if not isinstance(value, bool):
            raise ValueError(option + " must be a boolean")
        result[variable] = str(value).lower()
    return result


def enabled(name):
    return os.getenv(name, "false").lower() == "true"
