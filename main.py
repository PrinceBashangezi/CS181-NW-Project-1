#!/usr/bin/env python3
"""
Unified P2P Chat Application
Combines all work into a single cohesive program
"""

import socket
import sys
import threading
import signal
from connection_manager import ConnectionManager
from prince import availableOptions, connect, list, terminate
from Sultan import send_command, start_receiver_thread
from bryson import get_local_ip


class P2PChatApp:
    def __init__(self, listening_port):
        self.listening_port = listening_port
        self.conn_manager = ConnectionManager()
        self.server_socket = None
        self.stop_event = threading.Event()
        self.server_thread = None
        
    def start_server(self):
        """Start the server to accept incoming connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('', self.listening_port))
            self.server_socket.listen(5)
            print(f"Server listening on port {self.listening_port}")
            
            while not self.stop_event.is_set():
                try:
                    self.server_socket.settimeout(1.0)
                    conn, addr = self.server_socket.accept()
                    
                    # Add incoming connection to manager
                    conn_id = self.conn_manager.add_connection(conn, addr[0], addr[1])
                    
                    # Start receiver thread for incoming connection
                    thread = start_receiver_thread(conn, addr[0], addr[1], 
                                                lambda s: self.conn_manager.remove_connection(conn_id))
                    self.conn_manager.set_receiver_thread(conn_id, thread)
                    
                    print(f"✓ Connection established from {addr[0]}:{addr[1]} (ID: {conn_id})")
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if not self.stop_event.is_set():
                        print(f"Server error: {e}")
                    break
                    
        except Exception as e:
            print(f"Failed to start server on port {self.listening_port}: {e}")
            self.stop_event.set()
    
    def handle_command(self, line):
        """Handle user commands"""
        if not line.strip():
            return
            
        parts = line.strip().split()
        cmd = parts[0].lower()
        
        try:
            if cmd == 'help':
                print(availableOptions())
                
            elif cmd == 'myip':
                print(get_local_ip())
                
            elif cmd == 'myport':
                print(self.listening_port)
                
            elif cmd == 'connect':
                if len(parts) != 3:
                    print("Usage: connect <destination> <port>")
                    return
                result = connect(parts[1], parts[2], self.conn_manager, get_local_ip(), self.listening_port)
                print(result.strip())
                
            elif cmd == 'list':
                result = list(self.conn_manager.get_all_connections())
                print(result.strip())
                
            elif cmd == 'terminate':
                if len(parts) != 2:
                    print("Usage: terminate <connection_id>")
                    return
                result = terminate(parts[1], self.conn_manager.get_all_connections())
                print(result.strip())
                
            elif cmd == 'send':
                if len(parts) < 3:
                    print("Usage: send <connection_id> <message>")
                    return
                send_command(line, self.conn_manager)
                
            elif cmd == 'exit':
                print("Exiting...")
                self.stop_event.set()
                self.cleanup()
                return True
                
            else:
                print(f"Unknown command: {cmd}")
                print(availableOptions())
                
        except Exception as e:
            print(f"Error executing command: {e}")
            
        return False
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_event.set()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Close all connections
        self.conn_manager.close_all_connections()
        
        # Wait for server thread to finish
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=2.0)
            print('Goodbye :P')
    
    def run(self):
        """Main application loop"""
        # Start server thread
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
        
        # Wait a moment for server to start
        import time
        time.sleep(0.5)
        
        if self.stop_event.is_set():
            print("Failed to start server. Exiting.")
            return
        
        print(f"P2P Chat Application started on port {self.listening_port}")
        print("Type 'help' for available commands")
        
        try:
            while not self.stop_event.is_set():
                try:
                    line = input('> ').strip()
                    if self.handle_command(line):
                        break
                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
        finally:
            self.cleanup()


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nReceived interrupt signal. Exiting...")
    sys.exit(0)


def main():
    if len(sys.argv) != 2:
        print('Usage: python3 main.py <listening_port>')
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        if port < 1 or port > 65535:
            print("Port must be between 1 and 65535")
            sys.exit(1)
    except ValueError:
        print("Port must be an integer")
        sys.exit(1)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and run the application
    app = P2PChatApp(port)
    app.run()


if __name__ == '__main__':
    main()
