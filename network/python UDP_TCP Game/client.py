import socket

player_name_1 = "Isbaitan_Ibrahim"
player_name_2 = "Suhaib_Khalid"
player_name_3 = "Nasser_Ahmad"

server_name = "192.168.1.23"
tcp_port=6000
udp_port=6001

# initiate 1 tcp socket for accepting incoming requests
TCP_socket_in = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCP_socket_in.bind(('', tcp_port))
TCP_socket_in.listen(1)

# initiate 1 udp socket for sending and receiving
UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
UDP_socket.bind(('', udp_port))

# initiate 1 tcp socket for sending connections
TCP_socket_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCP_socket_out.settimeout(10)

# try and connect to server in order to join the game using TCP socket
try:
    TCP_socket_out.connect((server_name, tcp_port))
    TCP_socket_out.send((f"JOINS {player_name_1}").encode())
    reply1 = TCP_socket_out.recv(1024).decode()
    if reply1.startswith("ERROR"):
        print(reply1)
        exit()
except socket.timeout:
    print("Server took too long to let me in")
    exit()

# connection established succesfully and I am inside the game
print(f"Connected as {player_name_1}\nUDP connection established\n")

# currently in the waiting list awaiting the game to start
while True:
    message, address = UDP_socket.recvfrom(1024)
    messageDecoded = message.decode()
    if(messageDecoded == "Starting"):
        break
    print(messageDecoded)

# get game start details from server using TCP socket
connection, address = TCP_socket_in.accept()
startMessage = connection.recv(1024).decode()
connection.close()

print(startMessage)

# start guessing the number from the server using UDP socket
while True:
    message, address = UDP_socket.recvfrom(1024)
    messageDecoded = message.decode()
    if messageDecoded.startswith("Enter your guess"):
        myGuess = input(messageDecoded)
        UDP_socket.sendto((f"{myGuess}").encode(), (server_name, udp_port))
        answer, address= UDP_socket.recvfrom(1024)
        answerDecoded = answer.decode()
        print(answerDecoded)
    else:
        if messageDecoded == "Leave":
            break
        if messageDecoded.startswith("**"):
            reply = input(messageDecoded)
            UDP_socket.sendto(reply.encode(), (server_name, udp_port))
        else:
            print(messageDecoded)

# get the result of the game declaring who is winner and the number from server using TCP socket
connection, address = TCP_socket_in.accept()
finalMessage = connection.recv(1024).decode()
connection.close()

print(finalMessage)