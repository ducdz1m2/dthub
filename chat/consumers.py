import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from .models import Conversation, Message

User = get_user_model()

# Global set để tracking users online
online_users = set()


class GlobalPresenceConsumer(AsyncWebsocketConsumer):
    """Consumer cho global presence tracking"""
    
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user_id = self.scope["user"].id
            
            # Thêm vào online set
            online_users.add(self.user_id)
            
            # Tham gia global presence group
            await self.channel_layer.group_add("global_presence", self.channel_name)
            await self.accept()
            
            # Thông báo cho mọi người rằng tôi đã online
            await self.channel_layer.group_send(
                "global_presence",
                {
                    "type": "presence_update",
                    "user_id": self.user_id,
                    "status": "online"
                }
            )
            
            # Gửi danh sách users online hiện tại
            await self.send(text_data=json.dumps({
                "type": "online_users_list",
                "online_users": list(online_users)
            }))
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "user_id"):
            # Xóa khỏi online set
            online_users.discard(self.user_id)
            
            # Thông báo cho mọi người rằng tôi đã offline
            await self.channel_layer.group_send(
                "global_presence",
                {
                    "type": "presence_update",
                    "user_id": self.user_id,
                    "status": "offline"
                }
            )
            
            await self.channel_layer.group_discard("global_presence", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data.get("type") == "get_online_users":
            # Gửi danh sách online users hiện tại
            await self.send(text_data=json.dumps({
                "type": "online_users_list",
                "online_users": list(online_users)
            }))

    async def presence_update(self, event):
        await self.send(text_data=json.dumps(event))
        
    async def new_message(self, event):
        await self.send(text_data=json.dumps(event))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.other_user_id = int(self.scope["url_route"]["kwargs"]["other_id"])
        
        if not self.user.is_authenticated:
            await self.close()
            return
            
        self.my_id = self.user.id
        ids = sorted([self.my_id, self.other_user_id])
        self.room_group_name = f"chat_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")
        
        print(f"DEBUG: Received message length: {len(message) if message else 0}")
        print(f"DEBUG: Message prefix: {message[:50] if message else 'None'}...")
        
        if message:
            # Check if message contains image
            is_image = message.startswith("[IMAGE:") and message.endswith("]")
            print(f"DEBUG: Is image: {is_image}")
            
            if is_image:
                # Extract image URL
                image_url = message[7:-1]  # Remove [IMAGE: and ]
                print(f"DEBUG: Extracted image URL: {image_url}")
                
                # Save image message
                await self.save_message(self.my_id, self.other_user_id, message, is_image=True)
                
                # Gửi tin nhắn đến room với image URL
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": message,
                        "image_url": image_url,
                        "sender_id": self.my_id,
                        "is_image": True
                    }
                )
            else:
                # Save text message
                await self.save_message(self.my_id, self.other_user_id, message, is_image=False)
                
                # Gửi tin nhắn đến room
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": message,
                        "sender_id": self.my_id,
                        "is_image": False
                    }
                )
            
            # Gửi notification global về tin nhắn mới
            await self.channel_layer.group_send(
                "global_presence",
                {
                    "type": "new_message",
                    "sender_id": self.my_id,
                    "receiver_id": self.other_user_id,
                    "message": message
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, text, is_image=False):
        u1_id, u2_id = sorted([sender_id, receiver_id])
        conv, _ = Conversation.objects.get_or_create(user1_id=u1_id, user2_id=u2_id)
        return Message.objects.create(conversation=conv, sender_id=sender_id, text=text, is_image=is_image)
