"""Regression checks for security configuration; no TensorFlow download required."""

import unittest
import warnings
from types import SimpleNamespace

from security_config import configure_security, secret_key, server_options


class SecurityConfigurationTests(unittest.TestCase):
    def test_unconfigured_keys_are_unpredictable(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            a, b = secret_key({}), secret_key({})
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 64)
        self.assertEqual(len(bytes.fromhex(a)), 32)

    def test_rejects_short_or_placeholder_keys(self):
        for value in ("change-me-in-production", "short", "replace-this-with-a-strong-secret", " x" * 16):
            with self.subTest(value=value), self.assertRaises(ValueError):
                secret_key({"FLASK_SECRET_KEY": value})

    def test_retains_configured_secret(self):
        value = "b" * 64
        self.assertEqual(secret_key({"FLASK_SECRET_KEY": value}), value)

    def test_session_cookie_defaults(self):
        app = SimpleNamespace(config={}, secret_key=None)
        configure_security(app, {"FLASK_SECRET_KEY": "a" * 64})
        self.assertEqual(app.secret_key, "a" * 64)
        self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")
        self.assertFalse(app.config["SESSION_COOKIE_SECURE"])
        self.assertEqual(app.config["MAX_CONTENT_LENGTH"], 256 * 1024)

    def test_secure_cookie_flag_requires_explicit_opt_in(self):
        app = SimpleNamespace(config={}, secret_key=None)
        configure_security(app, {"FLASK_SECRET_KEY": "a" * 64, "FLASK_COOKIE_SECURE": "yes"})
        self.assertTrue(app.config["SESSION_COOKIE_SECURE"])
        with self.assertRaises(ValueError):
            configure_security(app, {"FLASK_SECRET_KEY": "a" * 64, "FLASK_COOKIE_SECURE": "maybe"})

    def test_default_server_is_loopback_without_debugger(self):
        self.assertEqual(server_options({}), {"host": "127.0.0.1", "port": 5000, "debug": False})

    def test_local_debug_is_opt_in(self):
        self.assertTrue(server_options({"FLASK_DEBUG": "true"})["debug"])

    def test_external_host_requires_secret_and_no_debug(self):
        with self.assertRaises(ValueError):
            server_options({"FLASK_HOST": "0.0.0.0"})
        with self.assertRaises(ValueError):
            server_options({"FLASK_HOST": "0.0.0.0", "FLASK_SECRET_KEY": "a" * 64, "FLASK_DEBUG": "true"})
        self.assertFalse(server_options({"FLASK_HOST": "0.0.0.0", "FLASK_SECRET_KEY": "a" * 64})["debug"])

    def test_rejects_bad_port_and_debug_flag(self):
        for p in ("0", "65536", "abc", "-1"):
            with self.subTest(port=p), self.assertRaises(ValueError):
                server_options({"PORT": p})
        with self.assertRaises(ValueError):
            server_options({"FLASK_DEBUG": "sometimes"})


if __name__ == "__main__":
    unittest.main()
