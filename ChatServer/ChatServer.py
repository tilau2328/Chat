import json
import os
import Pyro4
import sys
import threading
import zmq

DEBUG = True

def tprint(msg):
    sys.stdout.write(msg + '\n> ')
    sys.stdout.flush()

def find_a_port(socket, starting_port):
    port = starting_port
    End = False
    while not End or port == starting_port + 1000:
        try:
            socket.bind('tcp://*:' + str(port))
            End = True
        except:
            port += 1
    return port

class Worker(threading.Thread):
    def __init__(self, pull_socket, push_socket, publish_socket):
        super(Worker, self).__init__ ()
        self.__pull = pull_socket
        self.__push = push_socket
        self.__pub  = publish_socket

    def run(self):
        while True:
            message = self.__pull.recv()
            self.__pub.send(message)

    def stop(self):
        self._Thread__stop()

class ChatServer():
    def __init__(self, host = "localhost"):
        self.__registered = False
        self.__host       = host
        self.__boot()

    def __setup_worker(self):
        self.__worker = Worker(self.__pull_socket, self.__push_socket, self.__publish_socket)

    def __boot(self):
        self.__ctx = zmq.Context()

        self.__pull_socket    = self.__ctx.socket(zmq.PULL)
        self.__publish_socket = self.__ctx.socket(zmq.PUB)
        self.__push_socket    = self.__ctx.socket(zmq.PUSH)

        self.__pull_port = find_a_port(self.__pull_socket, 8000)
        self.__pub_port  = find_a_port(self.__publish_socket,  9000)
        self.__setup_worker()

    def register(self, ns_host, ns_port):
        try:
            self.__ns = Pyro4.Proxy("PYRONAME:nameserver.servers")
            self.__ns.register(self.__host, self.__pull_port, self.__pub_port)
            self.__registered = True
            return True
        except:
            return False

    def start(self):
        self.__worker.start()
        self.__stopped = False
        while not self.__stopped:
            if DEBUG:
                print "E: to exit"
                print "S: to send a message to another server"
                print "P: to publish a message to the clients"
                cmd = raw_input("> ")
                cmd = cmd.split(":")
                if cmd[0] == "E":
                    self.__stopped = True
                elif cmd[0] == "S":
                    dest = ":".join(cmd[1:])
                    tprint("send message to: " + dest)
                    try:
                        self.__push_socket.connect("tcp://" + dest)
                        message = raw_input("Message> ")
                        self.__push_socket.send(message)
                        self.__push_socket.close()
                    except:
                        tprint("failed")
                elif cmd[0] == "P":
                    message = ":".join(cmd[1:])
                    self.__publish_socket.send(message)
                else:
                    print "invalid command"

    def stop(self):
        self.__worker.stop()
        self.__pull_socket.close()
        self.__publish_socket.close()
        self.__push_socket.close()
        if self.__registered:
            self.__ns.unregister()
            self.__registered = False
        self.__stopped = True

def main():
    os.system('clear')
    server = ChatServer()
    if server.register("localhost", 7999) or DEBUG:
        server.start()
    else:
        print "Unable to register server"
    server.stop()
    os.system('clear')

if __name__ == '__main__':
    main()