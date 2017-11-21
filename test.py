#!/usr/bin/env python
from server import SERVR_HOST, SERVER_PORT, WEBSOCKET_ENDPOINT
from unittest import TestCase
import httplib
import subprocess
import time

class TestClient(TestCase):
    def setUp(self):
        self.connection_url = "%s:%s" % (SERVR_HOST, str(SERVER_PORT))
        self.subprocess = subprocess.Popen("exec python ./server.py", stdout=subprocess.PIPE, shell=True)
        time.sleep(1)

    def test_http_method_not_allowed_request(self):
        conn = httplib.HTTPConnection(self.connection_url)
        conn.request("POST", "")
        response = conn.getresponse()
        self.assertEqual(response.status, httplib.METHOD_NOT_ALLOWED)

    def test_http_request(self):
        conn = httplib.HTTPConnection(self.connection_url)
        conn.request("GET", "")
        response = conn.getresponse()
        self.assertEqual(response.status, httplib.OK)

    def test_websocket(self):
        headers = {'Upgrade': 'WebSocket',
                   'Connection': 'Upgrade'}
        conn = httplib.HTTPConnection(self.connection_url)
        conn.request("GET", WEBSOCKET_ENDPOINT, headers=headers)
        response = conn.getresponse()
        data = response.read()
        self.assertEqual(response.status, httplib.BAD_REQUEST)
        self.assertIn("Missing Sec-WebSocket-Key header", data)

        headers = {'Upgrade': 'WebSocket',
                   'Connection': 'Upgrade',
                   'Sec-WebSocket-Key': '9aJYEbnLCWvczRQALUVpce=='}
        conn = httplib.HTTPConnection(self.connection_url)
        conn.request("GET", WEBSOCKET_ENDPOINT, headers=headers)
        response = conn.getresponse()
        self.assertEqual(response.status, httplib.SWITCHING_PROTOCOLS)
        self.assertIn(('connection', 'Upgrade'), response.getheaders())
        self.assertIn(('upgrade', 'WebSocket'), response.getheaders())

    def tearDown(self):
        self.subprocess.kill()

if __name__ == '__main__':
    unittest.main()
