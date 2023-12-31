from enum import Enum
from db import Users, Chats
import pymongo
import time
from functools import wraps
from .exc import NotExistedChat, PermissionDeniedError
from app.config import MONGODB_CONNECTION_URI


class ChatType(Enum):
    PRIVATE = 'private'
    GROUP = 'group'

class Chat:
    def __init__(self, chat_id, user: Users, chat_type=None, new=False) -> None:
        self.client = pymongo.MongoClient(MONGODB_CONNECTION_URI)
        self.db = self.client['chats']
        self.collection = self.db[chat_id]
        self.user = user
        self.chat_id = chat_id
        if new:
            self.create_rights(chat_type)
        if not new:
            self.__check_permission()


    def create_rights(self, chat_type):
        users = Chats.query.filter_by(id=self.chat_id)
        user_ids = []
        for item in users:
            user_ids.append(item.user_id)

        rights = {
            'chat_config': {
                'users': user_ids,
                'title': self.chat_id,
                'type': chat_type
            }
        }
        if chat_type == ChatType.PRIVATE:
            pass
        elif chat_type == ChatType.GROUP:
            rights['chat_config']['creator_id'] = self.user.id

        self.collection.insert_one(rights)

    def get_config(self):
        result = self.collection.find_one({'chat_config': {'$exists': True}})
        return result.get('chat_config')

    def check_rights(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            result = self.collection.find_one({'chat_config': {'$exists': True}})
            if result:
                chat_config = result.get('chat_config')
                users = chat_config.get('users')
                if self.user.id in users:
                    return f(self, *args, **kwargs)
                else:
                    raise PermissionDeniedError()
            elif result is None:
                raise NotExistedChat(f'Chat with ID {self.chat_id} does not exist')
        return wrapper

    @check_rights
    def __check_permission(self):
        pass

    @check_rights
    def send_message(self, message):
        last_message = next(self.collection.find({'message': {'$exists': True}}).sort([("message_id", -1)]).limit(1), None)
        next_message_id = 1
        if last_message:
            next_message_id = last_message.get('message_id') + 1
            
        current_time = time.time()
        self.collection.insert_one({
            'from': self.user.login,
            'from_id': self.user.id,
            'message': message,
            'time': current_time,
            'message_id': next_message_id
        })
        return next_message_id

    @check_rights
    def get_count_chat_messages(self):
        last_message = next(self.collection.find({'message': {'$exists': True}}).sort([("message_id", -1)]).limit(1), None)
        if last_message:
            count_msg = last_message.get('message_id')
        elif last_message is None:
            count_msg = 0
        return count_msg

    @check_rights
    def get_chat_messages(self, count=20, offset=0):
        cursor = self.collection.find({'message': {'$exists': True}}).sort([("message_id", -1)]).limit(count).skip(offset)
        messages = []
        
        for document in cursor:
            document.pop("_id", None)
            messages.append(document)
            
        return messages
    
    @check_rights
    def change_chat_title(self, new_title):
        result = self.collection.update_one({'chat_config': {'$exists': True}}, {'$set': {'chat_config.title': new_title}})
        return result.modified_count

    @check_rights
    def add_user(self, user_id):
        result = self.collection.update_one({'chat_config': {'$exists': True}}, {'$push': {'chat_config.users': user_id}})
        return result.matched_count