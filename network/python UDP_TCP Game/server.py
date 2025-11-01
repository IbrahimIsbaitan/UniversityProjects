import random
import socket
import threading
import time

tcp_port = 6000
udp_port = 6001
min_players = 2
max_players = 4
to_enter_your_guess = 10
to_start_game = 10
game_duration = 60

# store all player names
playersNames=[]
# store for each player his address as to be able to connect with him in the future
playerAddress={}

numLowBound=1
numHighBound=100

secretNumber = random.randint(numLowBound, numHighBound)

# initiate TCP socket for accepting connections
TCP_socket_in = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TCP_socket_in.bind(('', tcp_port))
TCP_socket_in.listen(max_players)
TCP_socket_in.settimeout(5)

# initiate TCP socket for sending connection requests
TCP_socket_out = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# initiate UDP socket for sending and receiving
UDP_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
UDP_socket.bind(('', udp_port))

waitingRoom = "Waiting Room:"
playersString = ""

# function to add player into the game using address of the player and the TCP connection
def addPlayer(connection, address):
    if len(playersNames) == max_players:
        return
    global waitingRoom
    global playersString

    clientMessage = connection.recv(1024).decode().strip()
    message=clientMessage.split()
    if len(message) == 2 and message[0] == "JOINS":
        newName = message[1]
        if newName in playersNames:
            connection.send("ERROR username is taken".encode())
        else:
            # add new player to waiting list of all other players using UDP
            for name in playersNames:
                UDP_socket.sendto(f"{newName}".encode(), (playerAddress[name], udp_port))
            playerAddress[newName]=address[0]
            playersNames.append(newName)
            waitingRoom += "\n" + newName
            if len(playersString) == 0:
                playersString=newName
            else:
                playersString+=", "+newName
            UDP_socket.sendto(f"{waitingRoom}".encode(), (address[0], udp_port))

            print(f"New connection from ({address[0]}, {address[1]}) as {newName}")
            connection.send("Connected succesfully".encode())

    else :
        connection.send("ERROR command not valid syntax".encode())
    connection.close()

# waits until minimum number of players join then wait to_start_game delay window until
# I start the game as to allow more players to join until I close window and start the game
# limited by the max_players allowed
def waitForPlayers():
    startTime =time.time()
    reachedMin = False
    while len(playersNames) < max_players and not (reachedMin and time.time()-startTime >= to_start_game):
        if len(playersNames) == min_players and not reachedMin:
            reachedMin = True
            startTime=time.time()
        
        # accept new player request to join using TCP socket
        try:
            connection, clientAddress = TCP_socket_in.accept()
            thread = threading.Thread(target=addPlayer, args=(connection, clientAddress))
            thread.start()
        except socket.timeout:
            continue

# send game results into all the players using TCP socket
def sendVictory(winner):
    for name in playersNames:
        if not name in playerAddress:
            continue
        UDP_socket.sendto("Leave".encode(), (playerAddress[name], udp_port))
        
        TCP_socket_out=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        TCP_socket_out.connect((playerAddress[name], tcp_port))
        TCP_socket_out.send((f"===GAME RESULTS===\nTarget number was: {secretNumber}\nWinnner: {winner}").encode())
        TCP_socket_out.close()

# remove player from the game if he is not active player and isnt playing
def removePlayer(leaverName):
    print(f"{leaverName} disconnected from the game!!")
    del playerAddress[leaverName]
    for name in playersNames:
        if not name in playerAddress:
            continue
        if len(playerAddress) == 1:
            # check if last player remaining and playing alone wants to continue playing using UDP socket
            UDP_socket.sendto((f"**{leaverName} decided to leave you alone in this game, do you want to continue? ").encode(), (playerAddress[name], udp_port))
            reply = UDP_socket.recv(1024).decode()
            if(reply.lower()=="yes") :
                return True
            else:
                return False
        else:
            # let all players know that this player disconnected from the game using UDP socket
            UDP_socket.sendto((f"{leaverName} disconnected from the game!!"), (playerAddress[name], udp_port))
    return len(playerAddress) != 0

# request guess from player using his address and UDP socket
def playerGuess(name):
    UDP_socket.sendto((f"Enter your guess ({numLowBound}, {numHighBound}): ").encode(), (playerAddress[name], udp_port))
    
    UDP_socket.settimeout(to_enter_your_guess)
    
    try:
        clientMessage, address = UDP_socket.recvfrom(1024)
        message = clientMessage.decode().strip().split()
        if len(message) != 1 or not message[0].isdigit():
            UDP_socket.sendto("Warning: not valid number".encode(), address)
        elif int(message[0])<numLowBound or int(message[0])>numHighBound:
            UDP_socket.sendto("Warning: number out of range".encode(), address)
        else:
            number = int(message[0])
            if number == secretNumber:
                UDP_socket.sendto("Feedback: Correct".encode(), address)
                return 1
            elif number<secretNumber:
                UDP_socket.sendto("Feedback: Higher".encode(), address)
            else:
                UDP_socket.sendto("Feedback: Lower".encode(), address)
    except socket.timeout:
        return -1
    return 0

# function to run the game and keep asking each player by turn
# to send his guess in using UDP socket
def runGame():
    # let all players know that we are starting the game using UDP
    # then let them know the details of the game using TCP
    for name in playersNames:
        UDP_socket.sendto("Starting".encode(), (playerAddress[name], udp_port))

        TCP_socket_out=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        TCP_socket_out.connect((playerAddress[name], tcp_port))
        TCP_socket_out.send((f"Game started with players: {playersString}\nYou have {game_duration} to guess the number ({numLowBound}-{numHighBound})!").encode())
        TCP_socket_out.close()

    start_time = time.time()
    
    # goodToContinue will check if there is more than 1 player
    # or if there is 1 player remaining but he wants to continue playing
    goodToContinue=True
    while time.time()-start_time<60 and goodToContinue:
        for name in playersNames:
            if not name in playerAddress:
                continue

            
            won = playerGuess(name)
            if won == 1:
                sendVictory(name)
                print(f"Game completed. Winner: {name}")
                return
            elif won == -1:
                goodToContinue = removePlayer(name)
                if not goodToContinue:
                    break
    sendVictory("No one won the game")
    print("Game completed. no winners")

secretNumber = random.randint(numLowBound, numHighBound)
playersNames=[]
players={}

hostName=socket.gethostname()
ip=socket.gethostbyname(hostName)

print(f"Server started on {ip}: TCP {tcp_port}, UDP: {udp_port}")
waitForPlayers()
print(f"Starting game with {len(playersNames)} players...")
runGame()