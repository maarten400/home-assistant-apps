import ast
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from run import prepare_x11_directory


class StartupTests(unittest.TestCase):
    def test_x11_permissions_and_owner(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / ".X11-unix"
            with patch("run.os.chown") as chown:
                prepare_x11_directory(path)
                self.assertTrue(path.is_dir())
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o1777)
                chown.assert_called_once_with(path, 0, 0)

    def test_x11_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "link"
            path.symlink_to(root)
            with self.assertRaises(RuntimeError):
                prepare_x11_directory(path)

    def test_all_nginx_temp_paths(self):
        text = Path(__file__).with_name("nginx.conf").read_text()
        for directive in ("client_body_temp_path", "proxy_temp_path", "fastcgi_temp_path", "uwsgi_temp_path", "scgi_temp_path"):
            self.assertRegex(text, directive + r"\s+/tmp/")

    def test_x11_setup_before_user_drop(self):
        tree = ast.parse(Path(__file__).with_name("run.py").read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)]
        prepare = next(n.lineno for n in calls if isinstance(n.func, ast.Name) and n.func.id == "prepare_x11_directory")
        drop = next(n.lineno for n in calls if isinstance(n.func, ast.Attribute) and n.func.attr == "setuid")
        self.assertLess(prepare, drop)


if __name__ == "__main__":
    unittest.main()
