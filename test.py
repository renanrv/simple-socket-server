#!/usr/bin/env python
from server import SERVER_HOST, SERVER_PORT, WEBSOCKET_ENDPOINT, get_encoded_frame, \
    OPCODE_TEXT, OPCODE_CLOSE
from unittest import TestCase
import httplib
import socket
import subprocess
import time
import unittest


class TestClient(TestCase):
    def setUp(self):
        self.connection_url = "%s:%s" % (SERVER_HOST, str(SERVER_PORT))
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

        self.assertEqual(response.status, httplib.BAD_REQUEST)
        self.assertIn("Missing Sec-WebSocket-Key header", response.read())

        headers = {'Upgrade': 'WebSocket',
                   'Connection': 'Upgrade',
                   'Sec-WebSocket-Key': '9aJYEbnLCWvczRQALUVpce==',
                   'Sec-WebSocket-Version': 13}
        conn = httplib.HTTPConnection(self.connection_url)
        conn.request("GET", WEBSOCKET_ENDPOINT, headers=headers)
        response = conn.getresponse()

        self.assertEqual(response.status, httplib.SWITCHING_PROTOCOLS)
        self.assertIn(('connection', 'Upgrade'), response.getheaders())
        self.assertIn(('upgrade', 'WebSocket'), response.getheaders())

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((socket.gethostbyname(SERVER_HOST), SERVER_PORT))

        data = "Hello, world!"
        sock.send(get_encoded_frame(data=data, opcode=OPCODE_TEXT))
        self.assertEqual("{'status': 'success'}", sock.recv(1024))

        sock.close()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((socket.gethostbyname(SERVER_HOST), SERVER_PORT))

        data = "Hello, again!"
        sock.send(get_encoded_frame(data=data, opcode=OPCODE_TEXT))
        self.assertEqual("{'status': 'success'}", sock.recv(1024))
        sock.close()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((socket.gethostbyname(SERVER_HOST), SERVER_PORT))

        data = "Bye!"
        sock.sendall(get_encoded_frame(data=data, opcode=OPCODE_CLOSE))
        self.assertEqual("{'status': 'success'}", sock.recv(1024))
        sock.close()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((socket.gethostbyname(SERVER_HOST), SERVER_PORT))

        data = "Hello, again!"
        sock.send(get_encoded_frame(data=data, opcode=OPCODE_TEXT))
        self.assertIn("HTTP/1.1 405 Method Not Allowed", sock.recv(1024))

        sock.close()

    def tearDown(self):
        self.subprocess.kill()


if __name__ == '__main__':
    unittest.main()
