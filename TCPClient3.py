"""
    Python 3
    Usage: python3 TCPClient3.py localhost <port> <udpPort>
    coding: utf-8
    
    Author: z5416488
"""


import select
from socket import *
import sys, time, queue, os, tqdm
import threading

#Server would be running on the same host as Client
if len(sys.argv) != 4:
    print("\n===== Error usage, python3 TCPClient3.py SERVER_IP SERVER_PORT UDP_PORT ======\n")
    exit(0)
serverHost = sys.argv[1]
serverPort = int(sys.argv[2])
serverAddress = (serverHost, serverPort)
udpPort = sys.argv[3]

# Function to initialize a UDP socket for the client
def initialize_udp_socket():
    client_udp_socket = socket(AF_INET, SOCK_DGRAM)
    client_udp_socket.bind((serverHost, int(udpPort)))
    return client_udp_socket


# Defined socket for client, used to communicate with the server
clientSocket = socket(AF_INET, SOCK_STREAM)

# define a thread for client that receives server messages
def listen(clientSocket):
    while True:
        data = clientSocket.recv(1024).decode()
        if not data:
            break
        
        # If the received message starts with "RECEIVE:", print the message content
        if "RECEIVE: " in data:
            msg = data.split(" ", 1)
            print(msg[1])
            
        # If the message indicates a presenter is sending a file, extract information and start presenter thread
        elif 'Presenter: ' in data:
            parts = data.split()
            ip = parts[1]
            udp = parts[2]
            filename = parts[3]
            time.sleep(0.2)
            presenter_thread = threading.Thread(target=presenter_state, args=(ip, udp, filename))
            presenter_thread.daemon = True
            presenter_thread.start()
        
        # If the message indicates an audience is receiving a file, extract information and start receive thread
        elif 'Audience: ' in data:
            parts = data.split()
            presenter = parts[1]
            filename = parts[2]
            audience = parts[3]
            
            udp_socket = initialize_udp_socket()
            receive_thread = threading.Thread(target=audience_state, args=(udp_socket, presenter, filename, audience))
            receive_thread.start()


# Function to handle presenter state, sending a file via UDP
def presenter_state(ip, udp, filename):
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    with open(filename, 'rb') as file:
        data = file.read(1024)
        print(f"\n{filename} has been uploaded")
        
        while data:
            udp_socket.sendto(data, (ip, int(udp)))
            data = file.read(1024)
        udp_socket.close()

# Function to handle audience state, receiving a file via UDP     
def audience_state(udp_socket, presenter_username, filename, audience):
    new_filename = f"{presenter_username}_{filename}"
    with open(new_filename, 'wb') as file:
        print(f"\nReceived {filename} from {presenter_username}\n")
        print("Enter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /p2pvideo, /logout):")

        while True:
            data, _ = udp_socket.recvfrom(1024)
            if not data:
                break
            file.write(data)


    print(f"\nFile {new_filename} has been received and saved.\n")
            

# Build connection with the server and send a login message
clientSocket.connect(serverAddress)
message = "Please login"
print(message)
clientSocket.sendall(message.encode())

loginStatus = False

data = clientSocket.recv(1024)
receivedMessage = data.decode()

while not loginStatus:

    # Receive response from the server
    # Parse the message received from the server and take corresponding actions 
    if receivedMessage == "":
        print("[recv] Message from server is empty!")
    elif receivedMessage == "user credentials request":
        # If the server requests user credentials, get username and password and send them to the server
        username = input("Enter username: ").strip()
        clientSocket.send(username.encode())
        
        while True:
            password = input("Enter password: ")
            clientSocket.send(password.encode())
            
            outcome = clientSocket.recv(1024).decode()
            if outcome == "Valid":
                # If credentials are valid, print welcome message, send UDP port, and start listening thread
                print("Welcome to CHATTER BUDDY")
                clientSocket.send(udpPort.encode())
                loginStatus = True
                serverThread = threading.Thread(target=listen, args=(clientSocket,))
                serverThread.daemon = True
                serverThread.start()
                break
            
            elif outcome == "Invalid":
                print("Invalid credentials. Please try again.")
            elif outcome == "Timeout":
                print("Invalid credentials. You have been blocked. Please try again later")
                exit(0)
            elif outcome == "Retry":
                print("Your account is blocked due to multiple login failures. Please try again later")
                exit(0)

# Main loop for the client to handle user commands
while loginStatus:
    time.sleep(0.3)
    ans = input('\nEnter one of the following commands (/msgto, /activeuser, /creategroup, /joingroup, /groupmsg, /p2pvideo, /logout): \n')
    
    if '/msgto' in ans:
        clientSocket.send(ans.encode())
        continue
    elif '/activeuser' in ans:
        clientSocket.send(ans.encode())
        continue
    elif '/creategroup' in ans:
        clientSocket.send(ans.encode())
        continue

    elif '/joingroup' in ans:
        clientSocket.send(ans.encode())
        continue
    
    elif '/groupmsg' in ans:
        clientSocket.send(ans.encode())
        continue

    elif '/p2pvideo' in ans:
        clientSocket.send(ans.encode())
        continue
    elif '/logout' in ans:
        # If logout command, send the command and print goodbye message
        clientSocket.send(ans.encode())
        print("Bye, " + username + "!")
        loginStatus = False
        continue

    else:
        print("\nError. Invalid command")
        clientSocket.send("error".encode())
        clientSocket.send(str(udpPort).encode())
        continue
# close the socket
clientSocket.close()