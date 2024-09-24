# chat/consumers.py
import json
import os

from channels.db import database_sync_to_async

from .redisUtils import RedisUtils

import aiohttp
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            # Explicitly accept the WebSocket connection
            # print("Accepting WebSocket connection")
            await self.accept()
            print("WebSocket connect() called")

            # Extract the sessionid from query parameters
            session_id = self.scope['query_string'].decode().split('=')[1]

            # Ensure the session is loaded based on the sessionid
            self.scope['session'] = await database_sync_to_async(
                self._get_session_from_id)(session_id)

         # Create temp user ID if not exists
            if not self.scope['session'].get('temp_user_id'):
                print("temp_user_id not exists")
                user_id = await RedisUtils.create_temp_user_id()

                # Ensure session is properly loaded before accessing it
                # await self.channel_layer.group_add("chat", self.channel_name)

                # Load session if not already loaded
                if 'session' not in self.scope:
                    self.scope['session'] = {}

                self.scope['session']['temp_user_id'] = user_id

                # print("done")
                # Save session after modification
                await database_sync_to_async(self.scope['session'].save)()
            else:
                print("temp_user_id exists")

                user_id = self.scope['session']['temp_user_id']
                # print(f"Existing temp user ID: {user_id}")
                # Fetch and send the 10 most recent messages
                recent_messages = await RedisUtils.get_messages(user_id)
                for message in recent_messages:
                    await self.send(text_data=json.dumps({'message': message['text'], 'type': message['type']}))



        except Exception as e:
            print(f"Error during connection: {e}")

    def _get_session_from_id(self, session_id):
        # Load the session from the session ID
        from django.contrib.sessions.backends.cache import SessionStore
        session = SessionStore(session_key=session_id)
        session.modified = False  # Avoid saving unless necessary
        return session

    async def disconnect(self, close_code):
        # Handle WebSocket disconnection
        pass



    async def receive(self, text_data):
        # Get temp user ID from session
        user_id = self.scope['session']['temp_user_id']
        # Receive message from WebSocket
        data = json.loads(text_data)
        question = data['question']
        await RedisUtils.store_message(user_id, question,'user')
        # print(question)

        # # Check if `question` is a coroutine, and if so, await it to get the actual value
        # if asyncio.iscoroutine(question):
        #     question = await question
        #
        # # Ensure that `question` is now a string
        # if not isinstance(question, str):
        #     # raise TypeError("Question must be a string")
        #     print("question is not a string")

        # Generate answer (This can be rule-based, AI, or random)
        answer = await self.generate_answer(question)

        # Store the answer in Redis after generating it
        await RedisUtils.store_message(user_id, answer,'bot')


        # Send the answer back to WebSocket
        # await self.send(text_data=json.dumps({
        #     'message': answer
        # }))

# 火山方舟版 api key简单模式：
    async def generate_answer(self, question):

        # print(question)

        api_url = f"https://ark.cn-beijing.volces.com/api/v3/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('API_KEY')}",  # Replace with your OpenAI API key
            "Content-Type": "application/json"
        }
        data = {
            "model": "ep-20240922110810-8njsc",
            # "model": "gpt-3.5-turbo",  # Specify the model you want to use
            "messages": [{"role": "user", "content": question}],
            "stream": True # Enable streaming
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, json=data) as response:
                    if response.status == 200:
                        # Initialize a buffer to store the full message
                        full_message = ""
                        stream_complete = False
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
                                            await self.send(text_data=json.dumps({'message': chunk_message,'type': 'bot'}))
                                    except json.JSONDecodeError:
                                        continue

                    # If the stream completes, avoid returning an error
                    if stream_complete:
                        return full_message
                    else:
                        return "Error: Failed to get a valid response."
        except aiohttp.ClientError as e:
            return f"Error connecting to API: {e}"
