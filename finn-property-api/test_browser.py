import unittest
from browser import is_challenge
from settings import settings


class BrowserHelpersTests(unittest.TestCase):
    def test_challenge(self):
        self.assertTrue(is_challenge('<script src="https://ct.captcha-delivery.com/c.js"></script>'))
        self.assertTrue(is_challenge('Please enable JS and disable any ad blocker'))
        self.assertFalse(is_challenge('<html>ordinary results</html>'))

    def test_defaults(self):
        result = settings({"api_key": "x" * 32})
        self.assertEqual(result["CHROMIUM_SANDBOX"], "true")
        self.assertEqual(result["BROWSER_SETUP_ENABLED"], "false")
        self.assertNotEqual(result["DATA_DIR"], result["BROWSER_PROFILE_DIR"])

    def test_setup(self):
        result = settings({"api_key": "x" * 32, "browser_setup_enabled": True})
        self.assertEqual(result["BROWSER_SETUP_ENABLED"], "true")

    def test_invalid_options(self):
        with self.assertRaises(ValueError):
            settings({"api_key": "short"})
        with self.assertRaises(ValueError):
            settings({"api_key": "x" * 32, "chromium_sandbox": "false"})


if __name__ == "__main__":
    unittest.main()
