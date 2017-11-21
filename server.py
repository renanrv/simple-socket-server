#!/usr/bin/env python

import socket, threading, time
import re
from base64 import b64encode
from hashlib import sha1

SERVER_HOST_PROTOCOL = "http"
SERVR_HOST = "localhost"
SERVER_PORT = 8000
WEBSOCKET_ENDPOINT = "/ws"
GUID = "398YTWA5-U832-85LO-72GZ-K2PM0FV64N80"


def get_response_general(is_websocket=False, is_method_not_allowed=False, is_bad_request=False):
    if is_bad_request:
        response_proto = 'HTTP/1.1'
        response_status = '400'
        response_status_text = 'Bad Request'
    elif is_method_not_allowed:
        response_proto = 'HTTP/1.1'
        response_status = '405'
        response_status_text = 'Method Not Allowed'
    elif is_websocket:
        response_proto = 'HTTP/1.1'
        response_status = '101'
        response_status_text = 'Web Socket Protocol Handshake'
    else:
        response_proto = 'HTTP/1.1'
        response_status = '200'
        response_status_text = 'OK'

    response_general = '%s %s %s' % (response_proto, response_status, \
                                     response_status_text)
    return response_general
        

def get_response_headers(is_websocket=False, body="", key=None, is_method_not_allowed=False, is_bad_request=False):
    if is_bad_request:
        response_headers = {
            'Content-Type': 'application/json; encoding=utf8',
            'Content-Length': '%d' % len(body),
            'Connection': 'close',
            'Access-Control-Allow-Origin': '*',
        }
    elif is_method_not_allowed:
        response_headers = {
            'Content-Type': 'application/json; encoding=utf8',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        }
    elif is_websocket:
        response_headers = {
            'Content-Type': 'application/json; encoding=utf8',
            'Upgrade': 'WebSocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Accept': key,
            'WebSocket-Origin': '%s://%s:%s' % (SERVER_HOST_PROTOCOL, SERVR_HOST, str(SERVER_PORT)),
            'WebSocket-Location': 'ws://%s:%s' % (SERVR_HOST, str(SERVER_PORT)),
            'WebSocket-Protocol': 'sample',
        }
    else:
        response_headers = {
            'Content-Type': 'application/json; encoding=utf8',
            'Content-Length': '%d' % len(body),
            'Connection': 'close',
            'Access-Control-Allow-Origin': '*',
        }
    response_headers = ''.join('%s: %s\n' % (k, v) for k, v in \
                          response_headers.iteritems())
    return response_headers


def handle(s):
    text = s.recv(1024)

    if "GET" not in text:
        body = ""
        response_general = get_response_general(is_method_not_allowed=True)
        response_headers = get_response_headers(is_method_not_allowed=True)

    else:
        start_index = text.index("GET") + 4
        end_index = text.index("HTTP/1.1", start_index)
        endpoint = text[start_index: end_index].strip()

        if endpoint == WEBSOCKET_ENDPOINT:
            websocket_key_pattern = re.search('Sec-WebSocket-Key:\s+(.*?)[\n\r]+', text)
            if websocket_key_pattern is not None:
                key = (websocket_key_pattern.groups()[0].strip())
                response_key = b64encode(sha1(key + GUID).digest())
                body = "{'status': 'success'}"
                response_general = get_response_general(is_websocket=True)
                response_headers = get_response_headers(is_websocket=True,
                                                        body=body,
                                                        key=response_key)
            else:
                body = "{'detail': 'Missing Sec-WebSocket-Key header'}"
                response_general = get_response_general(is_bad_request=True)
                response_headers = get_response_headers(body=body,
                                                        is_bad_request=True)
        else:
            body = "{'status': 'fail'}"
            response_general = get_response_general(is_websocket=False)
            response_headers = response_headers = get_response_headers(is_websocket=False,
                                                                       body=body)

    s.send(response_general )
    s.send('\n')
    s.send(response_headers)
    s.send('\n')
    s.send(body)
    s.close()


if __name__ == '__main__':
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', SERVER_PORT));
    s.listen(1);
    while 1:
      t,_ = s.accept();
      threading.Thread(target = handle, args = (t,)).start()
