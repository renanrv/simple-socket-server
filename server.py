#!/usr/bin/env python
from base64 import b64encode
from hashlib import sha1
import array
import os
import re
import six
import socket
import struct
import threading


SERVER_HOST_PROTOCOL = "http"
SERVER_HOST = "localhost"
SERVER_PORT = 8000
WEBSOCKET_ENDPOINT = "/ws"
GUID = "398YTWA5-U832-85LO-72GZ-K2PM0FV64N80"
OPCODE_TEXT = 0x1
OPCODE_CLOSE = 0x8


def _mask(mask_key, data):
    """Apply mask to data based on mask_key."""
    for i in range(len(data)):
        data[i] ^= mask_key[i % 4]

    if six.PY3:
        return data.tobytes()
    else:
        return data.tostring()


def get_masked(data):
    """Return masked data for websocket frame."""
    mask_key = os.urandom(4)
    if data is None:
        data = ""

    bin_mask_key = mask_key
    if isinstance(mask_key, six.text_type):
        bin_mask_key = six.b(mask_key)

    if isinstance(data, six.text_type):
        data = six.b(data)

    _mask_array = array.array("B", bin_mask_key)
    _data_array = array.array("B", data)
    masked_data = _mask(_mask_array, _data_array)

    if isinstance(mask_key, six.text_type):
        mask_key = mask_key.encode('utf-8')
    return mask_key + masked_data


def get_encoded_frame(data="", opcode=OPCODE_TEXT, mask=1):
    """Return encoded frame."""
    if opcode == OPCODE_TEXT and isinstance(data, six.text_type):
        data = data.encode('utf-8')

    length = len(data)
    fin, rsv1, rsv2, rsv3, opcode = 1, 0, 0, 0, opcode

    frame_header = chr(fin << 7 | rsv1 << 6 | rsv2 << 5 | rsv3 << 4 | opcode)

    if length < 0x7e:
        frame_header += chr(mask << 7 | length)
        frame_header = six.b(frame_header)
    elif length < 1 << 16:
        frame_header += chr(mask << 7 | 0x7e)
        frame_header = six.b(frame_header)
        frame_header += struct.pack("!H", length)
    else:
        frame_header += chr(mask << 7 | 0x7f)
        frame_header = six.b(frame_header)
        frame_header += struct.pack("!Q", length)

    if not mask:
        return frame_header + data
    return frame_header + get_masked(data)


def is_close_frame(frame):
    """Return True if frame has close connection opcode."""
    frame_byte_array = [ord(character) for character in frame]
    if frame_byte_array[0] == 136:
        return True
    return False


def get_decoded_frame(frame):
    """Return decoded frame data."""
    frame_byte_array = [ord(character) for character in frame]
    frame_length = frame_byte_array[1] & 127
    first_mask_index = 2

    if frame_length == 126:
        first_mask_index = 4
    elif frame_length == 127:
        first_mask_index = 10

    masks = [m for m in frame_byte_array[first_mask_index:first_mask_index + 4]]

    first_data_byte_index = first_mask_index + 4
    decoded_data = []
    i = first_data_byte_index
    j = 0
    while i < len(frame_byte_array):
        decoded_data.append(chr(frame_byte_array[i] ^ masks[j % 4]))
        i += 1
        j += 1

    return decoded_data


def get_response_general(is_websocket=False, is_method_not_allowed=False, is_bad_request=False):
    """Return a string with proper response general data."""
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

    response_general = '%s %s %s' % (response_proto, response_status, response_status_text)
    return response_general


def get_response_headers(is_websocket=False, body="", key=None, is_method_not_allowed=False):
    """Return a string with proper response headers."""
    if is_method_not_allowed:
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
            'WebSocket-Origin': '%s://%s:%s' % (SERVER_HOST_PROTOCOL,
                                                SERVER_HOST,
                                                str(SERVER_PORT)),
            'WebSocket-Location': 'ws://%s:%s' % (SERVER_HOST,
                                                  str(SERVER_PORT)),
            'WebSocket-Protocol': 'sample',
        }
    else:
        response_headers = {
            'Content-Type': 'application/json; encoding=utf8',
            'Content-Length': '%d' % len(body),
            'Connection': 'close',
            'Access-Control-Allow-Origin': '*',
        }
    response_headers = ''.join('%s: %s\n' % (k, v) for k, v in
                               response_headers.iteritems())
    return response_headers


def handle(s, source_address):
    """Handle socket execution."""
    text = s.recv(1024)

    response_general = None
    response_headers = None
    should_close_connection = True
    if source_address in successful_handshake_clients:
        should_close_connection = is_close_frame(text)
        if should_close_connection:
            successful_handshake_clients.remove(source_address)
        body = "{'status': 'success'}"
    elif "GET" not in text:
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
                body = "{'status': 'upgraded'}"
                response_general = get_response_general(is_websocket=True)
                response_headers = get_response_headers(is_websocket=True,
                                                        body=body,
                                                        key=response_key)
                should_close_connection = False
                successful_handshake_clients.append(source_address)
            else:
                body = "{'detail': 'Missing Sec-WebSocket-Key header'}"
                response_general = get_response_general(is_bad_request=True)
                response_headers = get_response_headers(body=body)
        else:
            body = "{'status': 'http'}"
            response_general = get_response_general(is_websocket=False)
            response_headers = get_response_headers(is_websocket=False,
                                                    body=body)

    if response_general:
        s.send(response_general)
        s.send('\n')
    if response_headers:
        s.send(response_headers)
        s.send('\n')
    s.send(body)
    if should_close_connection:
        s.close()


if __name__ == '__main__':
    successful_handshake_clients = []
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', SERVER_PORT))
    s.listen(1)
    while 1:
        t, source_address = s.accept()
        threading.Thread(target=handle, args=(t, source_address[0])).start()
