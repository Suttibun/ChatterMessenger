"""
    ServerSide
    Python 3
    Usage: python3 TCPserver3.py localhost <input>
    coding: utf-8
    
    Author: z5416488
"""


from socket import *
from threading import Thread
import sys, select, time, logging, datetime, os

# acquire server host and port from command line parameter
if len(sys.argv) != 3:
    print("\n===== Error usage, python3 TCPServer3.py SERVER_PORT ======\n")
    exit(0)
if int(sys.argv[2]) < 1 or int(sys.argv[2]) > 5:
    print("Credential currentAttempt out of bounds")
    exit(0)
    
serverHost = "127.0.0.1"
serverPort = int(sys.argv[1])
serverAddress = (serverHost, serverPort)
maxAttempt = int(sys.argv[2])
user_states = {}
active_users = {}
message_counter = 0
group_counter = 0
blockedUsers = {}
activeUsersThread = {}
group_chats = {}
group_dm_count = 0

# define socket for the server side and bind address
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(serverAddress)


# Function to get UDP port for a user from userlog.txt
def getUDP(user):
    with open("userlog.txt", "r") as file:
        for line in file:
            if user in line:
                userline = line
                break;
        
        if userline:
            elements = userline.split(';')
            udp_port = elements[-1].strip()
    return udp_port


# Function to get IP address for a user from userlog.txt
def getIP(user):
    with open("userlog.txt", "r") as file:
        userline = None 
        for line in file:
            if user in line:
                userline = line
                break  # Exit the loop once the user is found

        if userline:
            elements = userline.split(';')
            ip_port = elements[-2].strip()
            return ip_port
        else:
            return None

"""
    Define multi-thread class for client
    This class would be used to define the instance for each connection from each client
    For example, client-1 makes a connection request to the server, the server will call
    class (ClientThread) to define a thread for client-1, and when client-2 make a connection
    request to the server, the server will call class (ClientThread) again and create a thread
    for client-2. Each client will be runing in a separate thread, which is the multi-threading
"""

class ClientThread(Thread):
    def __init__(self, clientAddress, clientSocket):
        Thread.__init__(self) 
        global activeUsersThread
        global active_users   
        self.clientAddress = clientAddress
        self.clientSocket = clientSocket
        self.clientAlive = False
        self.logStatus = False
        self.timeOut = 0
        self.username = ""
        self.id = len(active_users) + 1
                
        print("===== New connection created for: ", clientAddress)
        self.clientAlive = True
        
    def run(self):
        message = ''
        
        while self.clientAlive:
            data = self.clientSocket.recv(1024)
            message = data.decode()
            
            if message == '':
                self.clientAlive = False
                print("===== the user disconnected - ", self.clientAddress)
                break
            
            if message == 'Please login':
                print("[recv] New login request")
                self.process_login()

            elif '/msgto' in message:                
                self.process_msgto(message)
                
            elif message == '/activeuser':
                print("[recv] Active user request")      
                print(self.username + " issued /activeuser command")          
                self.active_user()
                
                  
            elif '/creategroup' in message:
                print("[recv] Create group")
                print(self.username + " issued /creategroup command")
                self.create_group(message)
                
            elif '/joingroup' in message:
                print("[recv] Join group")
                print(self.username + " issued /joingroup command")
                self.join_group(message)
                
            elif '/groupmsg' in message:
                self.group_message_formatter(message)
                
            elif '/p2pvideo' in message:
                print("[recv] Process P2P")
                self.process_p2p(message)
                
            elif message == '/logout':
                print("[recv] Logout request")
                self.process_logout()
            
            else:
                print("[recv] " + message)
                print("[send] Cannot understand this message")
                message = 'Cannot understand this message'
                self.clientSocket.send(message.encode())
    
    """
        You can create more customized APIs here, e.g., logic for processing user authentication
        Each api can be used to handle one specific function, for example:
        def process_login(self):
            message = 'user credentials request'
            self.clientSocket.send(message.encode())
    """
    
    # Function to authenticate user credentials
    def authenticate(self, data_file, username, password):
        if data_file.strip() == username or data_file.strip() == password:
            return False
        
        with open("credentials.txt", "r") as file:
            for line in file:
                if data_file.strip() == line.strip():
                    return True
            return False
    
    # Function to handle login process
    def process_login(self):
        global active_users
        message = 'user credentials request'
        print('[send] ' + message)
        self.clientSocket.send(message.encode())
        username = self.clientSocket.recv(1024).decode()
        currentAttempt = 0
        outcome = "Invalid"
        
        while currentAttempt < maxAttempt:
            if not self.logStatus:             
                password = self.clientSocket.recv(1024).decode()
                login = username + " " + password    

            if username in blockedUsers:
                if datetime.datetime.now() < blockedUsers[username]:
                    outcome = "Retry" 
                    self.clientSocket.send(outcome.encode())
                    count = 0
                    break   
            if self.authenticate(login, username, password):
                self.logStatus = True
                outcome = "Valid"
                self.clientSocket.send(outcome.encode())
                
                udpPort = self.clientSocket.recv(1024).decode()
                current_time = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")

                with open("userlog.txt", "a") as f:
                    f.write((str(self.id)) + "; " + str(current_time)+ "; " + username + "; " + clientAddress[0] + "; " + udpPort + "\n")
                
                self.username = username
                active_users[username] = f"{username}, active since {current_time} " + clientAddress[0] + " " + udpPort
                activeUsersThread[username] = self
                print(self.username + " is online")
                break
            else:
                currentAttempt += 1
            
            if self.logStatus == False and currentAttempt >= maxAttempt:
                outcome = "Timeout"
                blockedUsers[username] = datetime.datetime.now() + datetime.timedelta(seconds=10)
            
            self.clientSocket.send(outcome.encode())
        
    # Function to format and send messages to individual users
    def message_formatter(self, message):
        global message_counter
        message_segments = message.split(" ", 2)
        
        print(str(len(message_segments)))
        
        if len(message_segments) == 3:
            command = message_segments[0]
            username = message_segments[1]
            content = message_segments[2]
            time = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")


            if username in active_users:
                message_counter += 1
                message_number = message_counter

                with open("messagelog.txt", "a") as f:
                    f.write(str(message_number) + "; " + time + "; " + self.username + "; " + content + "\n")

                confirmation = "RECEIVE: \nmessage " + str(message_number) + " sent at " + time
                self.clientSocket.send(confirmation.encode())
                self.send_message(username, content, time)
            else:
                error_msg = "RECEIVE: \nInvalid User"
                print("Message was not successfully sent")
                self.clientSocket.send(error_msg.encode())

        else:
            error = '\nError. Incorrect arguments for /msgto format.'
            print("[send] " + error)
            self.clientSocket.send(error.encode())

    def send_message(self, username, msg, timeStamp):
        messaging_thread = activeUsersThread.get(username, None)
        if messaging_thread:
            messaging_thread.clientSocket.send("receive msg".encode())
            time.sleep(0.1)
            print("Return messages: " + username + ", active since" + timeStamp);
            time.sleep(0.1)
            receive = "RECEIVE: \n" + timeStamp + ", " + self.username + ": " + msg
            messaging_thread.clientSocket.send(receive.encode())
            time.sleep(0.1)
            messaging_thread.clientSocket.send("RECEIVE: \nEnter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /p2pvideo, /logout): ".encode())
        return


    def process_msgto(self, message):
        print("[recv] Message user")
        self.message_formatter(message);

    def active_user(self):
        message = "display user request"
        print("[send] " + message)
        self.clientSocket.send(message.encode())
       
        time.sleep(0.1)
        if len(active_users) <= 1:
            message = 'RECEIVE: \nNo other active user'
            self.clientSocket.send(message.encode())
        else:
            print("Return active user list:\n")
            for user in active_users:
                if user != self.username:
                    msg = 'RECEIVE: \n' + active_users[user]
                    print(f"{active_users[user]}\n")
                    self.clientSocket.send(msg.encode())
                
    def process_logout(self):
        self.clientAlive = False
        print(self.username + " logout")
        time.sleep(0.1)
        self.clientSocket.close()

    def create_group(self, message):
        global group_chats
        global group_counter
        message_parts = message.split()
        group_name = message_parts[1]
    
        
        if len(message_parts) < 3:
            print("Return message: Group chat room is not created. Please enter at least one more active users.")
            error_msg = "RECEIVE: \nPlease enter at least one more active users."
            self.clientSocket.send(error_msg.encode())
        else:
            group_members = message_parts[2:]
            
            if len(group_members) < 1:
                error_msg = "RECEIVE: \nError: A group must have at least 2 members."
                self.clientSocket.send(error_msg.encode())
            elif len(group_members) > 2:
                error_msg = "RECEIVE: \nError: A group must have at less than 4 members."
                self.clientSocket.send(error_msg.encode())
        
            else:
                if not group_name.isalnum():
                    error_msg = "RECEIVE: \nError: Group name must consist of letters and digits only."
                    self.clientSocket.send(error_msg.encode())
                elif group_name in group_chats:
                    error_msg = f"RECEIVE: \nError: A group chat with the name '{group_name}' already exists."
                    self.clientSocket.send(error_msg.encode())
                else:       
                    all_members_exist = all(member in active_users for member in group_members)
                    group_chats[group_name] = {self.username: {"confirmed_join": True}}
                    if all_members_exist:
                        group_counter += 1
                        group_number = group_counter
                        group_chats[group_name].update({member: {"confirmed_join": False} for member in group_members})
                        time = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")
                        
                        with open(group_name + ".txt", "a") as f:
                            pass
                            
                        confirmation_msg = f"RECEIVE: \nGroup chat room has been created, room name: {group_name}, users in this room: {' '.join(group_members)}"
                        self.clientSocket.send(confirmation_msg.encode())
                        
                    else:
                        # members that are not active
                        missing_members = [member for member in group_members if member not in active_users]
                        error_msg = "RECEIVE: \nError: Some group members are not active users: " + ", ".join(missing_members)
                        self.clientSocket.send(error_msg.encode())

    
    # Function to handle /joingroup command
    def join_group(self, message):
        global group_chats
        
        group_name = message.split()[1]
        if group_name in group_chats:
            if self.username in group_chats[group_name] and not group_chats[group_name][self.username]["confirmed_join"]:
                group_chats[group_name][self.username]["confirmed_join"] = True
                confirmation_msg = f"RECEIVE: \nYou have successfully joined the group chat: {group_name}."
                
                if self.username in group_chats[group_name] and group_chats[group_name][self.username]["confirmed_join"]:
                    group_chats[group_name][self.username]["confirmed_join"] = True
    
                    # Get a list of all members in the group chat
                    members = [member for member, data in group_chats[group_name].items()]
                    print(f"RECEIVE: \nReturn message: Join group chat room successfully, room name: {group_name}, users in this room: {' '.join(members)}.")
                
            
                self.clientSocket.send(confirmation_msg.encode())
            elif self.username in group_chats[group_name] and group_chats[group_name][self.username]["confirmed_join"]:
                error_msg = "RECEIVE: \nError: You are already a member of this group chat."
                self.clientSocket.send(error_msg.encode())
            else:
                error_msg = "RECEIVE: \nError: You are not eligible to join this group chat."
                self.clientSocket.send(error_msg.encode())
                
        else:
            error_msg = "RECEIVE: \nError: The group chat does not exist."
            self.clientSocket.send(error_msg.encode())
            
            
    # Function to format and send messages to a group
    def group_message_formatter(self, message):
        global group_dm_count
        
        group_message = message.split(' ')[2:]
        group_name = message.split(' ')[1]
        time = datetime.datetime.now().strftime("%d %b %Y %H:%M:%S")
        group_message = ' '.join(group_message)

        
        if group_name in group_chats and self.username in group_chats[group_name] and group_chats[group_name][self.username]["confirmed_join"]:
            group_dm_count += 1
            message_number = group_dm_count
            formatted_message = f"{message_number}; {time}; {self.username}; {group_message}\n"
            
            with open(group_name + ".txt", "a") as f:
                f.write(formatted_message)
            
            confirmation_msg = "RECEIVE: \nGroup chat message sent."
            self.clientSocket.send(confirmation_msg.encode())
            self.group_send_message(group_name, group_message, time)
            
    # Function to send a group message to all members of the group
    def group_send_message(self, group_name, group_message, timeStamp):
        for member, data in group_chats[group_name].items():
            if member != self.username and data["confirmed_join"]:
                group_messaging_thread = activeUsersThread.get(member, None)
                print(group_messaging_thread)
                if group_messaging_thread:
                    group_messaging_thread.clientSocket.send("receive msg".encode())
                    time.sleep(0.1)
                    receive = "RECEIVE: \n" + timeStamp + ", " + group_name + ", " + self.username + ": " + group_message
                    group_messaging_thread.clientSocket.send(receive.encode())
                    time.sleep(0.1)
                    group_messaging_thread.clientSocket.send("RECEIVE: \nEnter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /p2pvideo, /logout): ".encode())
                return
            
        else:
            error_msg = "Error: You are not eligible to send messages to this group chat."
            self.clientSocket.send(error_msg.encode())       
        
    # Function to process /p2pvideo command
    def process_p2p(self, message):
        parts = message.split()
        receiving_username = parts[1]
        filename = parts[2]

    
        if len(parts) != 3:
            error_msg = "RECEIVE: \nError: Invalid /p2pvideo command format."
            self.clientSocket.send(error_msg.encode())
            return
        
        if receiving_username in active_users:
            udp = getUDP(receiving_username).strip()
            ip = getIP(receiving_username).strip()
            message = f"{udp} and {ip} address and File: {filename}"
            
            self.clientSocket.send((f"Presenter: {ip} {udp} {filename}").encode())
            
            receiver_thread = activeUsersThread.get(receiving_username, None)
            receiver_thread.clientSocket.send(f"Audience: {self.username} {filename} {receiving_username}".encode())
        else:
            print(f"RECEIVE: \nError: {username} is offline")


    
print("\n===== Server is running =====")
print("===== Waiting for connection request from clients...=====")


while True:
    serverSocket.listen()
    clientSockt, clientAddress = serverSocket.accept()
    clientThread = ClientThread(clientAddress, clientSockt)
    clientThread.start()