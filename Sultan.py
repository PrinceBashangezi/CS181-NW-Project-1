import threading
import socket
import os
import hashlib
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

    # state for file receiving
    receiving_file = False
    file_obj = None
    file_bytes_remaining = 0
    file_name = None
    expected_checksum = None
    file_hasher = None

    try:
        # prevent blocking forever
        sock.settimeout(1.0)

        while True:
            try:
                data = sock.recv(4096)
                if not data:  # peer closed
                    # Clean up any partially received file
                    if receiving_file:
                        if file_obj:
                            file_obj.close()
                            file_obj = None
                        if file_name and os.path.exists(file_name):
                            try:
                                os.remove(file_name)
                                print(f'Connection closed during file transfer. Incomplete file "{file_name}" deleted.')
                            except:
                                pass
                    break

                buf += data

                while True:
                    # 1) if we are NOT currently receiving a file, process header/chat lines
                    if not receiving_file:
                        i = buf.find(b'\n')
                        if i == -1:
                            # no complete line yet
                            break

                        line = buf[:i].decode('utf-8', 'replace')
                        buf = buf[i+1:]  # drop this line from buffer

                        # check if this line is a file header
                        if line.startswith('__FILE__ '):
                            # expected format: __FILE__ <filename> <size> <checksum>
                            parts = line.split(' ', 3)
                            if len(parts) != 4:
                                print('Received malformed file header.')
                                continue

                            file_name_raw = parts[1]
                            try:
                                file_bytes_remaining = int(parts[2])
                            except ValueError:
                                print('Received file header with invalid size.')
                                continue
                            
                            expected_checksum = parts[3].strip()

                            # make sure we don't accidentally create weird paths
                            file_name = os.path.basename(file_name_raw)
                            
                            # Initialize hasher for checksum verification
                            file_hasher = hashlib.sha256()
                            
                            try:
                                file_obj = open(file_name, 'wb')
                            except OSError as e:
                                print(f'Error opening file "{file_name}" for writing: {e}')
                                # skip reading the file payload, but still consume bytes
                                receiving_file = False
                                file_obj = None
                                file_bytes_remaining = 0
                                file_name = None
                                expected_checksum = None
                                file_hasher = None
                                continue

                            receiving_file = True
                            print(f'Starting to receive file "{file_name}" '
                                  f'({file_bytes_remaining} bytes) from {peer_ip}:{peer_port}')
                            # loop continues; next iteration will go into "receiving_file" branch

                        else:
                            # normal chat message (the original behavior)
                            print(f'Message received from {peer_ip}')
                            print(f"Sender's Port: {peer_port}")
                            print(f'Message: "{line}"')

                    # 2) if we ARE currently receiving a file, consume raw bytes
                    else:
                        if file_bytes_remaining <= 0:
                            # should not happen, but be safe
                            if file_obj:
                                file_obj.close()
                                file_obj = None
                            # Clean up corrupted file if it exists
                            if file_name and os.path.exists(file_name):
                                try:
                                    os.remove(file_name)
                                except:
                                    pass
                            print(f'File "{file_name}" received from {peer_ip}:{peer_port}')
                            receiving_file = False
                            file_obj = None
                            file_name = None
                            expected_checksum = None
                            file_hasher = None
                            continue

                        if not buf:
                            # need more data from the socket
                            break

                        # write as much as we can from buf into the file
                        chunk = buf[:file_bytes_remaining]
                        file_bytes_remaining -= len(chunk)
                        buf = buf[len(chunk):]
                        
                        # Update checksum as we receive data
                        if file_hasher:
                            file_hasher.update(chunk)
                        
                        # Write to file
                        if file_obj:
                            file_obj.write(chunk)

                        if file_bytes_remaining == 0:
                            # file complete - verify checksum before finalizing
                            if file_obj:
                                file_obj.close()
                                file_obj = None
                            
                            # Calculate checksum of received data
                            if file_hasher:
                                received_checksum = file_hasher.hexdigest()
                            else:
                                # Should not happen, but handle gracefully
                                print(f'ERROR: Checksum calculator not initialized for file "{file_name}"')
                                received_checksum = None
                            
                            # Verify checksum matches
                            if received_checksum and received_checksum == expected_checksum:
                                print(f'File "{file_name}" received successfully from {peer_ip}:{peer_port}')
                                print(f'Checksum verified: {received_checksum[:16]}...')
                            else:
                                # Checksum mismatch - file is corrupted
                                print(f'ERROR: File "{file_name}" is corrupted! Checksum mismatch.')
                                print(f'Expected: {expected_checksum[:16]}...')
                                print(f'Received: {received_checksum[:16]}...')
                                # Delete the corrupted file
                                try:
                                    if file_name and os.path.exists(file_name):
                                        os.remove(file_name)
                                        print(f'Corrupted file "{file_name}" has been deleted.')
                                except Exception as e:
                                    print(f'Warning: Could not delete corrupted file: {e}')
                            
                            # Reset state
                            receiving_file = False
                            file_obj = None
                            file_name = None
                            expected_checksum = None
                            file_hasher = None
                            # then we loop back and process any remaining buf as chat/header

            except socket.timeout:
                # normal; just loop again and try to recv more
                continue

    except (ConnectionResetError, BrokenPipeError, OSError):
        # peer force-closed / network error
        pass
    except Exception as e:
        print(f'Error in receiver loop: {e}')
    finally:
        # cleanup connection via callback
        try:
            if conn_id is not None:
                on_socket_close(conn_id)
            else:
                on_socket_close(sock)
        except Exception:
            pass


