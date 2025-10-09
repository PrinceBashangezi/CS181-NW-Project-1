import threading
import socket
MAX_MSG_LEN = 100
def send_command(full_line: str, conn_manager):
    """
    Send a message to a specific connection
    full_line: complete command line (e.g., "send 1 Hello World")
    conn_manager: ConnectionManager instance
    """
    # parse: send <id> <message...>
    try:
        _, id_str, msg = full_line.split(maxsplit=2)
    except ValueError:
        print('Usage: send <connection id> <message>')
        return

    if len(msg) > MAX_MSG_LEN:
        print(f'Error: message too long ({len(msg)} > {MAX_MSG_LEN}).')
        return

    try:
        cid = int(id_str)
    except ValueError:
        print('Error: connection id must be an integer.')
        return

    # get socket using connection manager
    conn_info = conn_manager.get_connection(cid)
    if not conn_info or 'sock' not in conn_info:
        print(f'Error: no connection with id {cid}.')
        return

    sock = conn_info['sock']
    try:
        sock.sendall((msg + '\n').encode('utf-8'))
        print(f'Message sent to {cid}')
    except OSError as e:
        print(f'Error: failed to send to {cid}: {e}')
        # Remove the connection if it's broken
        conn_manager.remove_connection(cid)


def start_receiver_thread(sock, peer_ip, peer_port, on_socket_close, conn_id=None):
    t = threading.Thread(target=_receiver_loop,
                         args=(sock, peer_ip, peer_port, on_socket_close, conn_id),
                         daemon=True)
    t.start()
    return t

def _receiver_loop(sock, peer_ip, peer_port, on_socket_close, conn_id=None):
    buf = b''
    try:
        # Set socket timeout to prevent blocking indefinitely
        sock.settimeout(1.0)
        while True:
            try:
                data = sock.recv(4096)
                if not data:  # Connection closed by peer
                    break
                buf += data
                while (i := buf.find(b'\n')) != -1:          # newline-framed messages
                    text = buf[:i].decode('utf-8', 'replace')
                    buf = buf[i+1:]
                    print(f'Message received from {peer_ip}')
                    print(f"Sender's Port: {peer_port}")
                    print(f'Message: "{text}"')
            except socket.timeout:
                # Timeout is normal, continue the loop
                continue
    except (ConnectionResetError, BrokenPipeError, OSError):
        # Connection was closed by peer
        pass
    except Exception as e:
        print(f'Error in receiver loop: {e}')
    finally:
        # Only call cleanup if the connection was actually closed
        try:
            if conn_id is not None:
                on_socket_close(conn_id)
            else:
                on_socket_close(sock)
        except Exception:
            pass

