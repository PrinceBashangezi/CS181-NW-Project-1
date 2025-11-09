import socket
import re
import os

def is_valid_ip(ip):
    """Validate IP address format (IPv4)"""
    try:
        # Check if it's a valid IPv4 address
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except:
        return False

def is_duplicate_connection(destination, port, conn_manager):
    """Check if we already have a connection to this destination:port"""
    connections = conn_manager.get_all_connections()
    for conn_info in connections.values():
        if conn_info['ip'] == destination and conn_info['port'] == port:
            return True
    return False

def availableOptions():
    return("""
Available commands:
  help                         - Show this help message
  myip                         - Display the IP address of this machine
  myport                       - Display the port this process is listening on
  connect <destination> <port> - Establish a TCP connection to the specified IP and port
  list                         - Display all active connections (ID, IP, port)
  terminate <connection_id>    - Close the connection with the specified ID
  send <connection_id> <msg>   - Send a message (up to 100 chars) to the specified connection
  sendfile <connection_id> <filepath> - Send a file to the specified connection
  exit                         - Close all connections and terminate the program
""")

def connect(destination, port, conn_manager, my_ip=None, my_port=None):
    """
    Establish a TCP connection to the specified IP and port
    destination: IP address to connect to
    port: port number to connect to
    conn_manager: ConnectionManager instance
    my_ip: current machine's IP (for self-connection check)
    my_port: current machine's port (for self-connection check)
    """
    # Validate IP address format
    if not is_valid_ip(destination):
        return f"Error: Invalid IP address format '{destination}'\n"
    
    # Validate port number
    try:
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            return f"Error: Port must be between 1 and 65535\n"
    except ValueError:
        return f"Error: Port must be an integer\n"
    
    # Check for self-connection
    if destination == my_ip or port_num == my_port:
        return f"Error: Cannot connect to self ({my_ip}:{port_num})\n"
    
    # Check for duplicate connection
    if is_duplicate_connection(destination, port_num, conn_manager):
        return f"Error: Already connected to {destination}:{port_num}\n"
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout for better reliability
        sock.connect((destination, port_num))        
        # Add to connection manager
        conn_id = conn_manager.add_connection(sock, destination, port_num)
        
        # Start receiver thread for this connection
        from Sultan import start_receiver_thread
        thread = start_receiver_thread(sock, destination, port_num, 
                                     lambda conn_id: conn_manager.remove_connection(conn_id), conn_id)
        conn_manager.set_receiver_thread(conn_id, thread)
        
        return f"✓ Connected to {destination} on port {port_num} (Connection ID: {conn_id})\n"
    except socket.timeout:
        return f"Error: Connection timeout to {destination}:{port_num}\n"
    except ConnectionRefusedError:
        return f"Error: Connection refused by {destination}:{port_num}\n"
    except socket.error as e:
        return f"Error: Failed to connect to {destination}:{port_num} - {e}\n"

def list(connections_dict):
    """
    Display all active connections (ID, IP, port)
    connections_dict: dictionary mapping connection_id to connection info
    """
    if not connections_dict:
        return "No active connections.\n"
    
    connectionslist = "id: IP address: \t Port No.\n"
    for conn_id, conn_info in connections_dict.items():
        connectionslist += f"{conn_id}: {conn_info['ip']} \t {conn_info['port']}\n"
    return connectionslist

def terminate(connection_id, connections_dict):
    """
    Close the connection with the specified ID
    connection_id: ID of the connection to terminate
    connections_dict: dictionary mapping connection_id to connection info
    """
    try:
        conn_id = int(connection_id)
        if conn_id in connections_dict:
            conn_info = connections_dict[conn_id]
            # Close the socket if it exists
            if 'sock' in conn_info:
                try:
                    conn_info['sock'].close()
                except:
                    pass
            # Remove from connections dictionary
            del connections_dict[conn_id]
            return f"Terminated connection {conn_id}\n"
        else:
            return f"Error: Connection {conn_id} not found\n"
    except ValueError:
        return "Error: Connection ID must be an integer\n"

def sendfile(connection_id, filepath, conn_manager):
    """
    Send a file to the specified connection
    connection_id: ID of the connection to send to
    filepath: path to the file to send
    conn_manager: ConnectionManager instance
    """
    # Validate connection ID
    try:
        conn_id = int(connection_id)
    except ValueError:
        return f"Error: Connection ID must be an integer\n"
    
    # Get connection info
    conn_info = conn_manager.get_connection(conn_id)
    if not conn_info or 'sock' not in conn_info:
        return f"Error: No connection with id {conn_id}\n"
    
    # Validate file exists and is readable
    if not os.path.exists(filepath):
        return f"Error: File '{filepath}' does not exist\n"
    
    if not os.path.isfile(filepath):
        return f"Error: '{filepath}' is not a file\n"
    
    try:
        # Get file size
        file_size = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        
        # Read file data
        with open(filepath, 'rb') as f:
            file_data = f.read()
        
        sock = conn_info['sock']
        
        # Send file header: FILE:<filename>:<size>\n
        header = f"FILE:{filename}:{file_size}\n"
        sock.sendall(header.encode('utf-8'))
        
        # Send file data
        sock.sendall(file_data)
        
        return f"File '{filename}' ({file_size} bytes) sent to connection {conn_id}\n"
        
    except PermissionError:
        return f"Error: Permission denied reading file '{filepath}'\n"
    except OSError as e:
        return f"Error: Failed to send file: {e}\n"
    except Exception as e:
        return f"Error: Unexpected error sending file: {e}\n"