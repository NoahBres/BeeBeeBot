import threading
from pathlib import Path
from collections import deque


import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import atexit


class Message(object):
    def __init__(self, message, sender, time=firestore.SERVER_TIMESTAMP):
        self.message = message
        self.sender = sender
        self.time = time

    @staticmethod
    def from_dict(source):
        message = Message(source["message"], source["sender"], source["time"])

        return message

    def to_dict(self):
        dest = {"message": self.message, "sender": self.sender, "time": self.time}

        return dest

    def __repr__(self):
        return (
            f"Message(message='{self.message}', sender={self.sender}, time={self.time})"
        )


class BeeBeeBot:
    def __init__(self, secret):
        self._secret = secret

        parent_path = Path(__file__).parent.absolute()
        service_account_file_path = parent_path / "service-account.json"

        cred = credentials.Certificate(str(service_account_file_path))
        firebase_admin.initialize_app(cred)

        self._db = firestore.client()

        print("Starting BeeBeeBot...🐝🐝\n")

        chat_collection = self._db.collection("chats")
        chat_ref = chat_collection.where("secret", "==", self._secret).get()

        if len(chat_ref) == 0:
            print("\n!!Your secret token is invalid!!")
            raise SystemExit
        else:
            self._chat_ref = chat_ref[0]
            self._messages_ref = chat_collection.document(self._chat_ref.id).collection(
                "messages"
            )

        self._message_queue = deque()

        self._watch_callback_done = threading.Event()
        self._watch_messages = self._messages_ref.on_snapshot(self.__on_snapshot)

        self._initial_messages_loaded = False

        atexit.register(self.__exit_handler)

    def __exit_handler(self):
        self._watch_messages.unsubscribe()

    def __on_snapshot(self, doc_snapshot, changes, read_time):
        if not self._initial_messages_loaded:
            self._initial_messages_loaded = True
            return

        new_messages = filter(lambda x: x.type.name == "ADDED", changes)
        new_messages = [
            Message.from_dict(message.document.to_dict()) for message in new_messages
        ]
        new_messages = sorted(new_messages, key=lambda x: x.time)

        # We filter out messages that aren't the bot's
        new_messages = filter(lambda x: x.sender != "bot", new_messages)

        self._message_queue.extend(new_messages)

        self._watch_callback_done.set()

    def send_message(self, msg):
        self._messages_ref.add(Message(msg, "bot").to_dict())

    def check_new_messages(self):
        if len(self._message_queue) == 0:
            return ""
        else:
            return self._message_queue.popleft().message