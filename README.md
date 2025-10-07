# CS181 Network Programming - P2P Chat Application

## Project Overview
This is a peer-to-peer chat application that allows multiple instances to connect and communicate with each other.

## Team Contributions
- **Prince**: `help`, `list`, `terminate` and `connect`
- **Sultan**: `send` command and received message handling
- **Bryson**: `myip`, `myport`, `exit`, socket creating and listening to incoming connections


## How to Run

### Option 1: Use the Unified Main Program (Recommended)
```bash or zsh
python3 main.py <listening_port>
```

## Available Commands
- `help` - Show available commands
- `myip` - Display this machine's IP address
- `myport` - Display the listening port
- `connect <destination> <port>` - Connect to another instance
- `list` - Show all active connections
- `send <connection_id> <message>` - Send message (max 100 chars)
- `terminate <connection_id>` - Close a connection
- `exit` - Close all connections and exit

## Example Usage
1. Start first instance: `python3 main.py 12345`
2. Start second instance: `python3 main.py 12346`
3. In second instance: `connect 127.0.0.1 12345`
4. Send messages: `send 1 Hello World!`
5. List connections: `list`
