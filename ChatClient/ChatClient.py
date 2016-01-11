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

def print_rooms(rooms):
    print "#rooms"
    if len(rooms) != 0:
        for room in rooms:
            print "-" + room
    else:
        print "empty list"

def def_username():
    End = False
    while not End:
        username = raw_input("Username> ")
        if username != "":
            return username

class Backend(threading.Thread):
    def __init__(self, ctx, output = None):
        super(Backend, self).__init__ ()
        self.__ctx     = ctx
        self.__running = False
        self.__boot(output)

    def __boot(self, output = None):
        self.__socket = self.__ctx.socket(zmq.SUB)
        self.__socket.setsockopt(zmq.SUBSCRIBE, "")
        if output == None:
            self.__print_message = tprint
        else:
            self.__print_message = output

    def connect(self, host, port):
        self.__host = host
        self.__port = port
        try:
            url = "tcp://" + host + ":" + str(port)
            self.__socket.connect(url)
        except:
            print "failed to connect backend to " + url

    def __is_running(self):
        return self.__running

    def disconnect(self):
        self.__socket.close()

    def process_message(self, message):
        try:
            message = json.loads(message)
            print message
            text = message["message"]
            text = message["from"] + ": " + text
            self.__print_message(text)
        except:
            self.__print_message(message)

    def stop(self):
        self.disconnect()
        self._Thread__stop()

    def run(self):
        self.__running = True
        while True:
            message = self.__socket.recv()
            self.process_message(message)

class Frontend(threading.Thread):
    def __init__(self, ctx):
        super(Frontend, self).__init__ ()
        self.__ctx = ctx
        self.__boot()

    def __boot(self):
        self.__socket = self.__ctx.socket(zmq.PUSH)

    def connect(self, host, port):
        self.__host = host
        self.__port = port
        try:
            url = "tcp://" + host + ":" + str(port)
            self.__socket.connect(url)
        except:
            print "failed to connect frontend to " + url

    def send(self, message):
        self.__socket.send(message)

    def stop(self):
        self.__socket.close()

class ChatClient():
    def __init__(self, output = None):
        self.__registered = False
        self.__connected = False
        self.__output = output
        self.__username = ""
        self.__current_room = None
        self.__ctx = zmq.Context()

    def register_to_nameserver(self, username, ns_host = "localhost", ns_port = 7999):
        try:
            if username == "":
                print "Invalid Username"
                return False
            self.__username = username
            self.__ns = Pyro4.Proxy("PYRONAME:nameserver.clients")
            self.__ns.register(username)
            self.__registered = True
            return True
        except:
            print "Unable to connect"
            return False

    def unregister(self):
        self.__ns.unregister(self.__username)

    def is_registered(self):
        return self.__registered

    def connect(self, host, frontend_port, backend_port):
        self.__frontend = Frontend(self.__ctx)
        self.__frontend.connect(host, frontend_port)
        self.__backend = Backend(self.__ctx, self.__output)
        self.__backend.connect(host, backend_port)
        self.__backend.start()
        self.__connected = True

    def disconnect(self):
        self.__frontend.stop()
        self.__backend.stop()
        self.__connected = False

    def is_connected(self):
        return self.__connected

    def get_room_list(self):
        room_list = self.__ns.get_room_list()
        return room_list

    def enter_room(self, RoomID):
        server = self.__ns.enter_room(RoomID, self.__username)
        try:
            self.connect(server["host"], server["pull_port"], server["pub_port"])
            self.__current_room = RoomID
            return True
        except:
            print "failed to connect to server"
            return False

    def leave_room(self):
        try:
            self.disconnect()
            self.__ns.leave_room(self.__username)
            self.__current_room = None
            return True
        except:
            return False

    def send_message(self, message, to = ""):
        if to == "":
            to = self.__current_room
        try:
            message = {
                "message": message,
                "from": self.__username,
                "to": to
            }
            self.__frontend.send(json.dumps(message))
        except:
            pass

    def room(self):
        End = False
        while not End:
            cmd = raw_input("> ")
            if cmd == "/exit":
                End = True
                self.leave_room()
            else:
                self.send_message(cmd)

    def stop(self):
        if self.__registered:
            self.unregister()
            if self.__connected:
                self.disconnect()
                self.__backend.exit()

    def run(self):
        End = False

        while not End:
            print "X: exit"
            print "L: List Room"
            print "E: Enter Room <RoomID>"
            cmd = raw_input("> ")
            if cmd == "X":
                End = True
            elif cmd == "L":
                rooms = self.__ns.get_room_list()
                print_rooms(rooms)
            elif cmd == "E":
                roomID = raw_input("RoomID> ")
                if self.__registered:
                    if roomID != "":
                        self.enter_room(roomID)
                        print "Room " + roomID
                        self.room()
                    else:
                        print "invalid room ID"
                else:
                    return

def main():
    os.system('clear')
    server = ChatClient()
    if DEBUG and len(sys.argv) == 3:
        server.connect("localhost", sys.argv[1], sys.argv[2])
    else:
        server.register_to_nameserver(def_username())

    if server.is_registered():
        server.run()

    server.stop()
    #os.system('clear')

if __name__ == '__main__':
    main()