#!/usr/bin/env python3
"""
Usage:
	python3 bryson.py <listening_port>

Commands supported:
	myip   - display this host's non-loopback IP address
	myport - display the port the process is listening on
	exit   - close listener and exit
"""

import socket
import sys
import threading
from prince import availableOptions, connect, list, terminate
from connection_manager import ConnectionManager
from Sultan import send_command


def get_local_ip():
	"""Return the first non-loopback IP for this host.

	Uses a short TCP connection to a public IP (doesn't send application
	data) to let the OS pick the outbound interface, then reads the
	socket's own address. Falls back to hostname lookup or 127.0.0.1 on error.
	"""
	try:
		# create_connection returns a connected socket; using a short timeout
		with socket.create_connection(('8.8.8.8', 80), timeout=1) as s:
			return s.getsockname()[0]
	except Exception:
		# Try hostname aliases (may return non-loopback addresses)
		try:
			hostname = socket.gethostname()
			addrs = socket.gethostbyname_ex(hostname)[2]
			for ip in addrs:
				if not ip.startswith('127.'):
					return ip
		except Exception:
			pass

		# Try getaddrinfo to discover any configured non-loopback IPv4 addresses
		try:
			for info in socket.getaddrinfo(socket.gethostname(), None):
				ip = info[4][0]
				# skip IPv6 and loopback
				if ':' in ip:
					continue
				if not ip.startswith('127.'):
					return ip
		except Exception:
			pass

		return '127.0.0.1'


class Listener(threading.Thread):
	def __init__(self, port, stop_event):
		super().__init__(daemon=True)
		self.port = port
		self.stop_event = stop_event
		self.sock = None

	def run(self):
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self.sock.bind(('', self.port))
			self.sock.listen(5)
		except Exception as e:
			print(f"Failed to listen on port {self.port}: {e}")
			self.stop_event.set()
			return

		self.sock.settimeout(1.0)
		while not self.stop_event.is_set():
			try:
				conn, addr = self.sock.accept()
			except socket.timeout:
				continue
			except Exception:
				break
			print(f"Incoming connection from {addr[0]}:{addr[1]} (auto-closed)")
			try:
				conn.close()
			except Exception:
				pass

		try:
			self.sock.close()
		except Exception:
			pass


def main():
	if len(sys.argv) != 2:
		print('Usage: python3 bryson.py <listening_port>')
		sys.exit(1)

	try:
		port = int(sys.argv[1])
	except ValueError:
		print('Port must be an integer')
		sys.exit(1)

	# Create connection manager
	conn_manager = ConnectionManager()
	
	stop_event = threading.Event()
	listener = Listener(port, stop_event)
	listener.start()

	try:
		while not stop_event.is_set():
			try:
				line = input('> ').strip()
			except EOFError:
				line = 'exit'

			if not line:
				continue

			parts = line.split()
			cmd = parts[0].lower()
			if cmd == 'myip':
				print(get_local_ip())
			elif cmd == 'myport':
				print(port)
			elif cmd == 'help':
				print(availableOptions())
			elif cmd == 'connect':
				if len(parts) != 3:
					print("Usage: connect <destination> <port>")
					continue
				print(connect(parts[1], parts[2], conn_manager, get_local_ip(), port).strip())
			elif cmd == 'list':
				print(list(conn_manager.get_all_connections()).strip())
			elif cmd == 'send':
				if len(parts) < 3:
					print('Usage: send <connection_id> <message>')
					continue
				send_command(line, conn_manager)
			elif cmd == 'terminate':
				if len(parts) != 2:
					print('Usage: terminate <connection_id>')
					continue
				print(terminate(parts[1], conn_manager).strip())
			elif cmd == 'exit':
				print('Exiting...')
				conn_manager.close_all_connections()
				stop_event.set()
				break
			else:
				print('Unknown command \n', availableOptions())

	except KeyboardInterrupt:
		stop_event.set()

	listener.join(timeout=2.0)
	print('Goodbye :P')


if __name__ == '__main__':
	main()




# example usage:
# python3 bryson.py 4545 <<'EOF'
# myip
# myport
# exit
# EOF