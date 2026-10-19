import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api_client


class Handler(BaseHTTPRequestHandler):
    attempts = {"flaky": 0}

    def _respond(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ok":
            self._respond(200, {"ok": True})
        elif self.path == "/missing":
            self._respond(404, {"error": "not found"})
        elif self.path == "/flaky":
            Handler.attempts["flaky"] += 1
            if Handler.attempts["flaky"] < 2:
                self._respond(500, {"error": "boom"})
            else:
                self._respond(200, {"recovered": True})
        elif self.path == "/auth":
            self._respond(200, {"auth": self.headers.get("Authorization")})
        else:
            self._respond(200, {})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        self._respond(201, {"received": payload})

    def log_message(self, *args):
        pass


class ApiClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def client(self, **kwargs):
        kwargs.setdefault("backoff", 0)
        kwargs.setdefault("sleeper", lambda _: None)
        return api_client.ApiClient(self.base, **kwargs)

    def test_get_json(self):
        self.assertEqual(self.client().get_json("/ok"), {"ok": True})

    def test_post_json(self):
        result = self.client().post_json("/echo", {"a": 1})
        self.assertEqual(result["received"], {"a": 1})

    def test_404_raises(self):
        with self.assertRaises(api_client.ApiError) as ctx:
            self.client().get_json("/missing")
        self.assertEqual(ctx.exception.status, 404)

    def test_retry_recovers(self):
        Handler.attempts["flaky"] = 0
        result = self.client(retries=2).get_json("/flaky")
        self.assertEqual(result, {"recovered": True})
        self.assertEqual(Handler.attempts["flaky"], 2)

    def test_no_retry_exhausted(self):
        Handler.attempts["flaky"] = 0
        with self.assertRaises(api_client.ApiError):
            self.client(retries=0).get_json("/flaky")

    def test_token_header(self):
        result = self.client(token="secret").get_json("/auth")
        self.assertEqual(result["auth"], "Bearer secret")

    def test_token_from_environment(self):
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, {"API_TOKEN": "envtoken"}):
            self.assertEqual(self.client().token, "envtoken")

    def test_connection_error(self):
        broken = api_client.ApiClient("http://127.0.0.1:1", retries=0, timeout=0.5)
        with self.assertRaises(api_client.ApiError):
            broken.get_json("/")


if __name__ == "__main__":
    unittest.main()
