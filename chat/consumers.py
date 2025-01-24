import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatMessage, UserActivity
from django.utils import timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.user = self.scope["user"]
            logger.info(f"Connection attempt by user: {self.user}")
            
            if not self.user.is_authenticated:
                logger.warning("Unauthenticated connection attempt")
                await self.close(code=4001)
                return

            # Update user activity
            await self.update_user_activity(True)  # Set as online

            self.user_room = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.user_room, self.channel_name)
            await self.accept()
            logger.info(f"WebSocket connection established for user: {self.user}")
            
            # Send connection confirmation
            await self.send(json.dumps({
                "type": "connection_established",
                "message": "Connected to chat server"
            }))
            
        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close(code=4002)

    async def disconnect(self, close_code):
        try:
            logger.info(f"WebSocket disconnected with code: {close_code}")
            
            # Update user activity to offline
            if hasattr(self, 'user') and self.user.is_authenticated:
                await self.update_user_activity(False)  # Set as offline
                
            if hasattr(self, 'user_room'):
                await self.channel_layer.group_discard(self.user_room, self.channel_name)
                
        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            recipient_id = data.get('recipient_id')

            if not message:
                await self.send(json.dumps({
                    'error': 'Message cannot be empty'
                }))
                return

            if not recipient_id:
                await self.send(json.dumps({
                    'error': 'Recipient ID is required'
                }))
                return

            # Validate recipient exists
            try:
                recipient = await self.get_recipient(recipient_id)
                if not recipient:
                    await self.send(json.dumps({
                        'error': 'Recipient not found'
                    }))
                    return
            except Exception as e:
                logger.error(f"Error validating recipient: {str(e)}")
                await self.send(json.dumps({
                    'error': 'Invalid recipient'
                }))
                return

            # Save message to database
            try:
                chat_message = await self.save_message(
                    sender=self.user,
                    recipient=recipient,
                    content=message
                )
                
                if not chat_message:
                    raise ValidationError("Failed to save message")

                message_data = {
                    "type": "chat_message",
                    "message": {
                        "id": chat_message.id,
                        "sender": self.user.username,
                        "sender_id": self.user.id,
                        "content": message,
                        "timestamp": chat_message.timestamp.isoformat(),
                    }
                }

                # Send to recipient
                await self.channel_layer.group_send(
                    f"user_{recipient_id}",
                    message_data
                )

                # Send confirmation to sender
                await self.channel_layer.group_send(
                    self.user_room,
                    message_data
                )

            except ValidationError as e:
                logger.error(f"Validation error saving message: {str(e)}")
                await self.send(json.dumps({
                    'error': str(e)
                }))
            except Exception as e:
                logger.error(f"Error saving message: {str(e)}")
                await self.send(json.dumps({
                    'error': 'Failed to save message. Please try again.'
                }))

        except json.JSONDecodeError:
            await self.send(json.dumps({
                'error': 'Invalid message format'
            }))
        except Exception as e:
            logger.error(f"Unexpected error in receive: {str(e)}")
            await self.send(json.dumps({
                'error': 'An unexpected error occurred'
            }))

    async def chat_message(self, event):
        try:
            message = event["message"]
            await self.send(text_data=json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")

    @database_sync_to_async
    def save_message(self, sender, recipient, content):
        try:
            return ChatMessage.objects.create(
                sender=sender,
                recipient=recipient,
                content=content
            )
        except Exception as e:
            logger.error(f"Database error saving message: {str(e)}")
            return None

    @database_sync_to_async
    def get_recipient(self, recipient_id):
        try:
            return User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting recipient: {str(e)}")
            return None

    @database_sync_to_async
    def update_user_activity(self, is_online):
        try:
            activity, _ = UserActivity.objects.get_or_create(user=self.user)
            activity.last_activity = timezone.now()
            activity.is_online = is_online
            activity.save()
            logger.info(f"Updated user activity for {self.user.username}: {'online' if is_online else 'offline'}")
        except Exception as e:
            logger.error(f"Error updating user activity: {str(e)}")