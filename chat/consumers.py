import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import Conversation, Message

User = get_user_model()


class GlobalConsumer(AsyncWebsocketConsumer):
    online_users = set()

    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user_id = self.scope["user"].id
            self.user_group_name = f"user_{self.user_id}"

            # Tham gia vào nhóm cá nhân để nhận tin nhắn riêng
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)

            # Tham gia vào nhóm chung để quản lý trạng thái Online/Offline
            await self.channel_layer.group_add("global_presence", self.channel_name)

            await self.accept()
            GlobalConsumer.online_users.add(self.user_id)

            # Thông báo cho mọi người là tôi vừa lên mạng
            await self.channel_layer.group_send(
                "global_presence",
                {
                    "type": "presence_update",
                    "user_id": self.user_id,
                    "status": "online",
                },
            )
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "user_id"):
            GlobalConsumer.online_users.discard(self.user_id)
            # Thông báo cho mọi người là tôi đã thoát web
            await self.channel_layer.group_send(
                "global_presence",
                {
                    "type": "presence_update",
                    "user_id": self.user_id,
                    "status": "offline",
                },
            )
            await self.channel_layer.group_discard("global_presence", self.channel_name)
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name
            )

    async def presence_update(self, event):
        # Gửi dữ liệu trạng thái xuống trình duyệt
        await self.send(text_data=json.dumps(event))

    # Trong chat/consumers.py -> class GlobalConsumer
    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get("action") == "request_status":
            # Phát tin nhắn online của chính mình cho toàn group
            await self.channel_layer.group_send(
                "global_presence",
                {
                    "type": "presence_update",
                    "user_id": self.user_id,
                    "status": "online",
                },
            )
        elif data.get("action") == "request_online_users":
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "online_users_list",
                        "online_users": list(GlobalConsumer.online_users),
                    }
                )
            )


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.my_id = self.scope["user"].id
        self.other_user_id = int(self.scope["url_route"]["kwargs"]["other_id"])
        ids = sorted([self.my_id, self.other_user_id])
        self.room_group_name = f"chat_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "typing":
            # Xử lý trạng thái đang nhập
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "user_typing",
                    "typing": data["typing"],
                    "user_id": self.my_id,
                },
            )
        else:
            # Xử lý gửi tin nhắn
            message = data.get("message")
            if message:
                # LƯU TIN NHẮN VÀO DATABASE
                await self.save_message(self.my_id, self.other_user_id, message)

                # Gửi tin nhắn tới cả nhóm
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat_message",
                        "message": message,
                        "sender_id": self.my_id,
                    },
                )

    # --- Các hàm Handler xử lý dữ liệu gửi xuống Client ---

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def user_typing(self, event):
        await self.send(text_data=json.dumps(event))

    # --- Hàm bổ trợ lưu DB (Database Sync to Async) ---

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, text):
        # Đảm bảo User1 luôn nhỏ hơn User2 theo đúng logic Conversation
        u1_id, u2_id = sorted([sender_id, receiver_id])

        # Tìm hoặc tạo cuộc hội thoại
        conv, _ = Conversation.objects.get_or_create(user1_id=u1_id, user2_id=u2_id)

        # Tạo tin nhắn mới
        return Message.objects.create(conversation=conv, sender_id=sender_id, text=text)
