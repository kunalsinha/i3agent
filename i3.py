import subprocess
import socket
import struct
import json
import threading

# i3 message types
MSG_RUN_COMMAND        = 0
MSG_GET_WORKSPACES     = 1
MSG_SUBSCRIBE          = 2
MSG_GET_OUTPUTS        = 3
MSG_GET_TREE           = 4
MSG_GET_MARKS          = 5
MSG_GET_BAR_CONFIG     = 6
MSG_GET_VERSION        = 7
MSG_GET_BINDING_MODES  = 8
MSG_GET_CONFIG         = 9
MSG_SEND_TICK          = 10
MSG_SYNC               = 11
MSG_GET_BINDING_STATE  = 12

# i3 event types
EVENT_WORKSPACE        = 'workspace'
EVENT_OUTPUT           = 'output'
EVENT_MODE             = 'mode'
EVENT_WINDOW           = 'window'
EVENT_BARCONFIG_UPDATE = 'barconfig_update'
EVENT_BINDING          = 'binding'
EVENT_SHUTDOWN         = 'shutdown'
EVENT_TICK             = 'tick'

def get_i3_socket_path():
    return subprocess.check_output(['i3', '--get_socketpath']).strip()

def _encode(msg_type, msg):
    return 'i3-ipc'.encode() + struct.pack('II', len(msg), msg_type) + msg.encode()

def _decode(blob):
    msg_length, msg_type = struct.unpack('II', blob[6:14])
    msg_type &= 0x7fffffff # turn off the most significant bit
    return msg_length, msg_type, blob[14:]

def send_msg(msg_type, msg=''):
    # Create socket
    i3_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # Connect socket
    i3_socket.connect(get_i3_socket_path())
    # Send msg to i3
    i3_socket.sendall(_encode(msg_type, msg))
    # Receive msg from i3
    _, msg = _receive(i3_socket)
    # Close the socket
    i3_socket.close()
    # Return response in json format
    return json.loads(msg)

def _receive(i3_socket):
    x = i3_socket.recv(14)
    total_msg_length, msg_type, msg = _decode(x)
    while len(msg) < total_msg_length:
        msg += i3_socket.recv(total_msg_length - len(msg))
    return msg_type, msg

def handle_subscription(i3_socket, handler):
    while True:
        event_type, msg = _receive(i3_socket)
        handler(event_type, json.loads(msg))

def subscribe(events, handler):
    # Create socket
    i3_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    # Connect socket
    i3_socket.connect(get_i3_socket_path())
    # Send subscription request to i3
    i3_socket.sendall(_encode(MSG_SUBSCRIBE, json.dumps(events)))
    # Receive reply from i3
    _, resp = _receive(i3_socket)
    # Check if subscription succeeded
    resp = json.loads(resp)
    if not resp.get('success'):
        raise Exception(f'Subscription failed: {resp}')
    # Handle subscribed events in a new thread
    handler_t = threading.Thread(target=handle_subscription, args=(i3_socket, handler), daemon=True)
    handler_t.start()

