# simple-socket-server
A simple socket server that accepts HTTP requests and upgrades a connection to WebSockets.

# Description
The server accepts an HTTP GET connection.
If the HTTP requests the enpoint '/ws', the server will upgrade the connection to WebSocket.

# Dependencies

* Python 2.7

# Setup

* `$ git clone https://github.com/renanrv/simple-socket-server.git
`
* `$ cd simple-socket-server`
* `$ python server.py`

# Tests
    python -m unittest -v test