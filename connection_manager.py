#!/usr/bin/env python3
"""
Connection Manager for tracking all active connections
"""

import socket
import threading
from typing import Dict, Any

class ConnectionManager:
    def __init__(self):
        self.connections: Dict[int, Dict[str, Any]] = {}
        self.next_connection_id = 1
        self.lock = threading.Lock()
    
    def add_connection(self, sock: socket.socket, peer_ip: str, peer_port: int) -> int:
        """Add a new connection and return its ID"""
        with self.lock:
            conn_id = self.next_connection_id
            self.next_connection_id += 1
            
            self.connections[conn_id] = {
                'sock': sock,
                'ip': peer_ip,
                'port': peer_port,
                'thread': None  # Will store receiver thread reference
            }
            return conn_id
    
    def remove_connection(self, conn_id: int) -> bool:
        """Remove a connection by ID"""
        with self.lock:
            if conn_id in self.connections:
                conn_info = self.connections[conn_id]
                try:
                    conn_info['sock'].close()
                except:
                    pass
                del self.connections[conn_id]
                print(f"Connection {conn_id} closed")
                return True
            return False
    
    def get_connection(self, conn_id: int) -> Dict[str, Any]:
        """Get connection info by ID"""
        with self.lock:
            return self.connections.get(conn_id, {})
    
    def get_all_connections(self) -> Dict[int, Dict[str, Any]]:
        """Get all active connections"""
        with self.lock:
            return self.connections.copy()
    
    def close_all_connections(self):
        """Close all active connections"""
        with self.lock:
            for conn_info in self.connections.values():
                try:
                    conn_info['sock'].close()
                except:
                    pass
            self.connections.clear()
    
    def set_receiver_thread(self, conn_id: int, thread: threading.Thread):
        """Set the receiver thread for a connection"""
        with self.lock:
            if conn_id in self.connections:
                self.connections[conn_id]['thread'] = thread
