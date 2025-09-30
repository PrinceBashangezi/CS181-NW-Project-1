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
from prince import availableOptions


def get_local_ip():
	"""Return the first non-loopback IP for this host.

	Uses a UDP socket to a public IP to pick the outbound interface without
	sending any data. Falls back to hostname lookup or 127.0.0.1 on error.
	"""
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
			s.connect(('8.8.8.8', 80))
			return s.getsockname()[0]
	except Exception:
		try:
			return socket.gethostbyname(socket.gethostname())
		except Exception:
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
			elif cmd == 'exit':
				print('Exiting...')
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