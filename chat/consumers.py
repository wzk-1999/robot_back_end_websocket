# chat/consumers.py
import json
import os

import jwt

from user.jwt_utils import JWTUtils
from .redisUtils import RedisUtils

import aiohttp
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Explicitly accept the WebSocket connection
            # print("Accepting WebSocket connection")
            await self.accept()

            # Extract JWT from cookies using the utility class
            headers = dict(self.scope['headers'])
            jwt_token = JWTUtils.extract_jwt_from_cookies(headers)

            # If JWT is found, decode it and use it
            if jwt_token:
                try:
                    decoded_token = JWTUtils.decode_jwt(jwt_token)
                    user_email = decoded_token.get('email')
                    # If JWT is valid, you can use user_email to fetch user data
                    # Fetch and send the 10 most recent messages
                    recent_messages = await RedisUtils.get_messages(user_email)
                    # print(recent_messages)
                    # Send the whole array of recent messages at once
                    await self.send(text_data=json.dumps({
                        'messages': recent_messages,
                    }))
                    return

                except jwt.ExpiredSignatureError:
                    await self.send(text_data=json.dumps({
                        'error': 'Token has expired'
                    }))
                    return
                except jwt.InvalidTokenError:
                    await self.send(text_data=json.dumps({
                        'error': 'Invalid token'
                    }))
                    return

            # If no JWT, fall back to extracting session ID from query string
            # Extract session ID from the query string
            session_id = None
            # print("go")
            query_string = self.scope['query_string'].decode()
            if "sessionid" in query_string:
                session_id = query_string.split('sessionid=')[1]

            # If session ID does not exist, create a new session
            if not session_id:
                # print("No session ID found, creating new session")
                user_id = await RedisUtils.create_temp_user_id()

                await self.send(text_data=json.dumps({'session_id': user_id}))
            else:
                # print("temp_user_id exists")

                # print(f"Existing temp user ID: {user_id}")
                # Fetch and send the 10 most recent messages
                recent_messages = await RedisUtils.get_messages(session_id)
                # print(recent_messages)
                # Send the whole array of recent messages at once
                await self.send(text_data=json.dumps({
                    'messages': recent_messages,
                }))

            # print("WebSocket connect() called")

        except Exception as e:
            print(f"Error during connection: {e}")

    # def _get_session_from_id(self, session_id):
    #     # Load the session from the session ID
    #     from django.contrib.sessions.backends.cache import SessionStore
    #     session = SessionStore(session_key=session_id)
    #     session.modified = False  # Avoid saving unless necessary
    #     return session

    async def disconnect(self, close_code):
        # Handle WebSocket disconnection
        pass



    async def receive(self, text_data):
        # Extract JWT from cookies using the utility class
        headers = dict(self.scope['headers'])
        jwt_token = JWTUtils.extract_jwt_from_cookies(headers)
        user_id = None

        if jwt_token:
            decoded_token = JWTUtils.decode_jwt(jwt_token)
            user_id = decoded_token.get('email')
        # If no JWT is found, fallback to sessionid in query string
        if not user_id:
            query_string = self.scope['query_string'].decode()
            if "sessionid" in query_string:
                user_id = query_string.split('sessionid=')[1]
        # Receive message from WebSocket
        data = json.loads(text_data)
        question = data['question']

        # print(question)

        # # Check if `question` is a coroutine, and if so, await it to get the actual value
        # if asyncio.iscoroutine(question):
        #     question = await question
        #
        # # Ensure that `question` is now a string
        # if not isinstance(question, str):
        #     # raise TypeError("Question must be a string")
        #     print("question is not a string")

        # Store user question in Redis, passing a custom TTL for logged-in users
        ttl = 3 * 86400 if jwt_token else 86400  # 3 days for logged-in users, 1 day for guests
        await RedisUtils.store_message(user_id, question, 'user', ttl)

        # Generate answer (This can be rule-based, AI, or random)
        answer = await self.generate_answer(user_id)


        # Store the answer in Redis after generating it
        await RedisUtils.store_message(user_id, answer,'assistant',ttl)


        # Send the answer back to WebSocket
        # await self.send(text_data=json.dumps({
        #     'message': answer
        # }))

# 火山方舟版 api key简单模式：
    async def generate_answer(self, user_id):

        messages_count= await RedisUtils.count_messages(user_id)
        # Fetch chat history from Redis
        chat_history = await RedisUtils.get_messages(user_id,messages_count)

        # Prepare messages for AI model, including context
        messages_for_ai = []
        for message in chat_history:
            messages_for_ai.append({"role": message['type'], "content": message['text']})
        #
        # # Add the user's question to the messages
        # messages_for_ai.append({"role": "user", "content": question})

        print(messages_for_ai)

        api_url = f"https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('API_KEY')}",  # Replace with your OpenAI API key
            "Content-Type": "application/json"
        }
        data = {
            "model": "ep-20240922110810-8njsc",
            # "model": "gpt-3.5-turbo",  # Specify the model you want to use
            # "messages": [{"role": "user", "content": messages_for_ai}],
            "messages":messages_for_ai,
            "stream": True # Enable streaming
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=data) as response:
                    stream_complete = False
                    if response.status == 200:
                        # Initialize a buffer to store the full message
                        full_message = ""

                        async for chunk in response.content.iter_any():
                            # Decode the chunk and process as needed
                            # print(chunk)
                            decoded_chunk = chunk.decode('utf-8').strip()
                            # print(f"decoded_chunk data is {decoded_chunk}")
                            if decoded_chunk:
                                # Some API services send JSON chunks, sometimes prefixed with data:
                                for line in decoded_chunk.splitlines():
                                    if line.startswith('data:'):
                                        line = line[len('data:'):].strip()
                                    # print(f"line data is {line}")
                                    # Process the chunk as JSON
                                    try:
                                        line_data = json.loads(line)
                                        # print(line_data)
                                        if 'choices' in line_data and line_data['choices']:
                                            chunk_message = line_data['choices'][0]['delta'].get('content', '')
                                            full_message += chunk_message
                                            # Check if streaming has finished
                                            if line_data['choices'][0].get('finish_reason') == 'stop':
                                                stream_complete = True
                                            # print(f"chunk_message is ${chunk_message}")

                                            # Optionally: Send partial responses if needed
                                            await self.send(text_data=json.dumps({'message': chunk_message}))
                                    except json.JSONDecodeError:
                                        continue

                    # If the stream completes, avoid returning an error
                    if stream_complete:
                        return full_message
                    else:
                        return "Error: Failed to get a valid response."
        except aiohttp.ClientError as e:
            return f"Error connecting to API: {e}"
