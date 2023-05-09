import logging
import sys
import socket
import time
from contextlib import contextmanager
from threading import Thread
from typing import Union

HOST = 'localhost'
PORT = 9999


def receive(client: socket.socket) -> None:
    """ Receives messages from chat """

    while True:
        try:
            msg = client.recv(1024).decode('utf-8')

            if msg == 'NICK':
                client.send(nick.encode('utf-8'))
            elif msg == 'CHANGE':
                new_nick = input('This username is already in use!\nPlease, choose another one: ')
                client.send(new_nick.encode('utf-8'))
            else:
                print(msg)
        except socket.error as e:
            logger.error(f"Error receiving data: {e}")
            sys.exit(1)


def send(client: socket.socket) -> None:
    """ Sends messages to chat """

    while True:
        msg = input()
        out_msg = f"{nick} ({time.strftime('%H:%M',time.localtime())}) >> {msg}"

        if msg == "/quit":
            try:
                client.send(msg.encode('utf-8'))
            except socket.error as e:
                logger.error(f'Error sending data: {e}')
            sys.exit(1)

        else:
            try:
                client.send(out_msg.encode('utf-8'))
            except socket.error as e:
                logger.error(f"Error sending data: {e}")

        logger.info(f'{out_msg}')


@contextmanager
def connect_socket(param1, param2) -> Union[None, socket.socket]:
    """
    Attempts to connect to the socket.
    Returns connection if succeed, throws error if failed.
    """
    s = socket.socket(param1, param2)
    try:
        yield s
    except Exception as e:
        print('Error:\n', e)
        sys.exit(1)


with connect_socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    nick = input("\nPlease, enter your NICKNAME: ")

    logging.basicConfig(level=logging.DEBUG,
                        filename=f'user_logs/{nick}.log',
                        format="%(message)s")
    logger = logging.getLogger(f"{nick}")

    try:
        s.connect((HOST, PORT))
    except socket.gaierror as e:
        logger.error(f"Address-related error connecting to server: {e}")
        sys.exit(1)
    except socket.error as e:
        logging.error(f"Connection error: {e}")
        sys.exit(1)

    in_thread = Thread(target=receive, args=(s,))
    in_thread.start()

    out_thread = Thread(target=send, args=(s,))
    out_thread.start()
