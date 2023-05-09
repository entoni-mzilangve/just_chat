import itertools
import os
import socket
import logging
import sys
import time
from contextlib import contextmanager
from threading import Thread
from typing import Union

sys_path = './sys_logs'

if not os.path.exists(sys_path):
    os.mkdir(sys_path)

logging.basicConfig(level=logging.DEBUG,
                    filename='sys_logs/system.log',
                    format="%(asctime)s | %(name)s >>> %(message)s")
logger = logging.getLogger("ADMIN")

HOST = 'localhost'
PORT = 9999
RETRY = 3

clients = []
users = []

COMMANDS = {
    '/cmd': 'Observe all possible chat commands',
    '/users': 'Get list of all registered users',
    '/syslogs': 'Obtain all logs concerning chat connection',
    '/logs [username]': 'Obtain all messages by a specific user',
}


def broadcast(msg: str, sender: socket.socket) -> None:
    """ Sends a message to all connected clients """

    for client in clients:
        if client != sender:
            for attempt in range(RETRY):
                try:
                    client.send(msg.encode('utf-8'))
                    break
                except socket.error as e:
                    index = clients.index(client)
                    addressee = users[index]

                    if attempt == RETRY - 1:
                        logger.error(f"Could not send data to {addressee}:\n{e}\n")
                        users.remove(addressee)
                        clients.remove(sender)
                        client.close()

                    logger.error(f"Error sending data to {addressee}:\n{e}\nTrying to reconnect {attempt}...")


def handle_conn(client: socket.socket) -> None:
    """ Handles and broadcasts messages from clients. """

    with client:
        while True:
            try:
                msg = client.recv(1024).decode('utf-8')
                if msg == '/quit':
                    raise Exception
                else:
                    if msg:
                        broadcast(msg, client)

            # означает ли это, что если я ничего не напишу => меня кикнут?
            except Exception as e:
                index = clients.index(client)
                nick = users[index]
                logger.error(f"Broken connection with {nick}")

                users.remove(nick)
                clients.remove(client)

                info_msg = f'****** {nick} has left {chat_name}! Total members = {len(users)}  ******'
                broadcast(info_msg, client)

                client.close()
                break


def administrate(server: socket.socket) -> None:
    """ Admin interface and commands. """

    logger_cmd = logging.getLogger("COMMAND")
    file_handler = logging.FileHandler('sys_logs/cmd.log')
    formatter = logging.Formatter("%(asctime)s | %(name)s == %(message)s")
    file_handler.setFormatter(formatter)
    logger_cmd.addHandler(file_handler)

    while True:
        print("\nPlease, ENTER '/cmd' to observe all commands.\n")
        msg = input('ADMIN: ')

        if msg == '/quit':
            logger_cmd.debug(f'{msg}')
            if users:
                info_msg = "\nADMIN has left chat!\nEverybody is OFFLINE!\nTill the next time, buddies!"
                broadcast(info_msg, server)

            server.close()
            break

        elif msg == '/users':
            logger_cmd.debug(f'{msg}')
            if users:
                for nick, client in itertools.zip_longest(users, clients):
                    print(users.index(nick) + 1, ' - ', nick, ' |\t', client.getpeername())
            else:
                print("Nobody is connected to this chat!(")

        elif msg.startswith('/logs'):
            logger_cmd.debug(f'{msg}')
            nickname = msg[5:].strip()

            if nickname in users:
                try:
                    with open(f"user_logs/{nickname}.log", mode='r') as f:
                        print(f.read())
                        logger.debug(f'Getting logs of {nickname}...')
                except FileNotFoundError:
                    print(f"No logs for {nickname}.")
            elif nickname == '':
                print("Please enter the name of requested user!")
            else:
                print(f"User '{nickname}' is not a member of this chat!")

        elif msg == '/syslogs':
            logger_cmd.debug(f'{msg}')
            try:
                with open(f"sys_logs/cmd.log", mode='r') as f:
                    lines = f.readlines()
                    print(*lines[-10:], sep='\n')
                    logger.debug(f'Getting logs syslogs...')
            except FileNotFoundError:
                print(f"No system logs at the moment.")

        elif msg == '/cmd':
            logger_cmd.debug(f'{msg}')
            print("\n<<< LIST of COMMANDS >>>")
            for cmd, info in COMMANDS.items():
                print(f'{cmd} || {info}')

        else:
            out_msg = f"*** ADMIN says *** ({time.strftime('%H:%M',time.localtime())}) >>>>:  "
            broadcast(out_msg, server)

    sys.exit()


@contextmanager
def connect_socket(param1, param2) -> Union[None, socket.socket]:
    """
    Attempts to connect to the socket.
    Returns connection if succeed, throws error if failed.
    """

    for attempt in range(RETRY):
        logger.debug(f'Attempt ({attempt+1}) to connect to socket...')
        s = socket.socket(param1, param2)

        try:
            yield s
            break
        except Exception as e:
            logger.error(f"Error creating socket: {e}\nTrying to reconnect({attempt+1}")
            print('Error: ', e)
            time.sleep(5)

    logger.critical('Reconnection failed!')
    sys.exit(1)


with connect_socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    chat_name = input("\nWhat's the name of this chat room?: ")
    print(f"\nChat '{chat_name}' created!\nWaiting for newcomers!...")

    cmd_thread = Thread(target=administrate, args=(s,))
    cmd_thread.start()

    while True:
        client, addr = s.accept()
        logger.info(f'New connection: {str(addr)}')

        while True:
            try:
                client.send('NICK'.encode('utf-8'))
            except socket.error as e:
                logger.error(f"Error sending data: {e}")
                client.close()

            try:
                nick = client.recv(1024).decode('utf-8')
            except socket.error as e:
                logger.error(f"Error receiving data: {e}")
                client.close()

            if nick not in users:
                users.append(nick)
                clients.append(client)
                break
            else:
                try:
                    client.send('CHANGE!'.encode('utf-8'))
                except socket.error as e:
                    logger.error(f"Error sending data: {e}")
                    client.close()
        try:
            msg = f"""
            \n~~~~~~~~ Successfully connected to {chat_name}! ~~~~~~~~
            Enter '/quit' to leave the chat!
            """
            client.send(msg.encode('utf-8'))
        except socket.error as e:
            logger.error(f"Error sending data: {e}")
            client.close()

        info_msg = f'\n****** Greet {nick} as a new chat member! ******\nTotal members = {len(users)}'
        broadcast(info_msg, client)
        print(f"\n{nick} connected to '{chat_name}'")
        logger.info(f'{nick} connected to chat!')

        thread = Thread(target=handle_conn, args=(client,))
        thread.start()
