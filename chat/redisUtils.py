import json

import redis
import time
import uuid

class RedisUtils:
    # Initialize Redis client (adjust host/port based on your Redis config)

    # because  redis.Redis(host='localhost', port=6379, db=1) is not async, so the operation using
    # this connection can't use await keyword
    redis_client = redis.Redis(host='localhost', port=6379, db=1)

    @staticmethod
    async def create_temp_user_id():
        # Create a new temp user ID
        user_id = str(uuid.uuid4())
        return user_id

    @staticmethod
    async def store_message(user_id, message, message_type, ttl=86400):
        timestamp = int(time.time())
        key = f"{user_id}:messages"
        # Store message as a JSON object including type
        message_data = json.dumps({'text': message, 'type': message_type})
        RedisUtils.redis_client.zadd(key, {message_data: timestamp})
        # Set TTL for 1 day for guest user(86400 seconds)
        # set ttl for 3 day if it's a loged in user (86400*3 seconds)
        RedisUtils.redis_client.expire(key, ttl)

    @staticmethod
    async def count_messages(user_id):
        key = f"{user_id}:messages"
        return RedisUtils.redis_client.zcard(key)

    @staticmethod
    async def get_messages(user_id, count=10):
        key = f"{user_id}:messages"
        # Get the most recent 'count' messages sorted by timestamp
        messages = RedisUtils.redis_client.zrange(key, -count, -1)  # Fetch most recent messages
        if messages is None:
            return []
        return [json.loads(message.decode('utf-8')) for message in messages]

    @staticmethod
    async def delete_temp_user_key(user_id):
        # Delete the Redis key for the user
        key = f"{user_id}:messages"
        RedisUtils.redis_client.delete(key)