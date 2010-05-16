print "Starting demo EPOLL timeserver..."
import datetime
import select
import socket

IP_ADDRESS = '0.0.0.0'
PORT_NUMBER = 2002
VERBOSE = False

EOL1 = '\n\r'
EOL2 = '\n\r\n'

response =  'HTTP/1.0 200 OK\r\n'
response += 'Date: Mon, 1 Jan 1996 01:01:01 GMT\r\n'
response += 'Content-Type: text/plain\r\n'
response += 'Content-Length: %(contentlength)s\r\n\r\n'
response += '%(content)s'

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((IP_ADDRESS, PORT_NUMBER))
server_socket.listen(True)
server_socket.setblocking(False)
server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

epoll = select.epoll()
epoll.register(server_socket.fileno(), select.EPOLLIN)
print "Listening on %s:%s" % (IP_ADDRESS, PORT_NUMBER)

def epoll_epollin(fileno):
	requests[fileno] += connections[fileno].recv(1024)
	if EOL1 in requests[fileno] or EOL2 in requests[fileno]:
		epoll.modify(fileno, select.EPOLLOUT)
		#TODO -2 magic number?
		if VERBOSE:
			print '-' * 40
			print requests[fileno].decode()[:-2]

def epoll_epollout(fileno):
	byteswritten = connections[fileno].send(responses[fileno])
	responses[fileno] = responses[fileno][byteswritten:]
	if len(responses[fileno]) == 0:
		epoll.modify(fileno, 0)
		connections[fileno].shutdown(socket.SHUT_RDWR)

def epoll_hup(fileno):
	epoll.unregister(fileno)
	connections[fileno].close()
	del connections[fileno]

epoll_func_map = dict([
	(select.EPOLLIN, epoll_epollin),
	(select.EPOLLOUT, epoll_epollout),
	(select.EPOLLHUP, epoll_hup)
])

def build_response(content):
	response_dict = {
		'content': content,
		'contentlength': len(content)
	}
	return response % response_dict

try:
	connections, requests, responses = {}, {}, {}
	while True:
		events = epoll.poll(1)
		for fileno, event in events:
			if fileno == server_socket.fileno():
				connection, address = server_socket.accept()
				connection.setblocking(False)
				epoll.register(connection.fileno(), select.EPOLLIN)
				connections[connection.fileno()] = connection
				requests[connection.fileno()] = ''
				response_msg = "Hello world!"
				responses[connection.fileno()] = build_response(repr(datetime.datetime.now()))
			else:
				epoll_func_map[event](fileno)
finally:
	epoll.unregister(server_socket.fileno())
	epoll.close()
	server_socket.close()
