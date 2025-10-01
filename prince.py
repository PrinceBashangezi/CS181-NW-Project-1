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
  exit                         - Close all connections and terminate the program
""")