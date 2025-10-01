import threading
MAX_MSG_LEN = 100
def send_command(full_line: str, connections: dict, table_lock: threading.Lock):
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

    # get socket under lock
    with table_lock:
        sock = connections.get(cid, {}).get("sock")
    if not sock:
        print(f'Error: no connection with id {cid}.')
        return

    try:
        sock.sendall((msg + '\n').encode('utf-8'))
        print(f'Message sent to {cid}')
    except OSError as e:
        print(f'Error: failed to send to {cid}: {e}')


def start_receiver_thread(sock, peer_ip, peer_port, on_socket_close):
    t = threading.Thread(target=_receiver_loop,
                         args=(sock, peer_ip, peer_port, on_socket_close),
                         daemon=True)
    t.start()
    return t

def _receiver_loop(sock, peer_ip, peer_port, on_socket_close):
    buf = b''
    try:
        while (data := sock.recv(4096)):
            buf += data
            while (i := buf.find(b'\n')) != -1:          # newline-framed messages
                text = buf[:i].decode('utf-8', 'replace')
                buf = buf[i+1:]
                print(f'Message received from {peer_ip}')
                print(f"Sender's Port: {peer_port}")
                print(f'Message: \"{text}\"')
    finally:
        try:
            on_socket_close(sock)
        except Exception:
            pass

