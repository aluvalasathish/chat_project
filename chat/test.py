from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from channels.auth import AuthMiddlewareStack
from .routing import websocket_urlpatterns
from .models import ChatMessage
import json

class ChatTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='user1', password='testpass123')
        self.user2 = User.objects.create_user(username='user2', password='testpass123')
        self.client.login(username='user1', password='testpass123')

    def test_chat_view(self):
        response = self.client.get(reverse('chat'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat/chat.html')

    def test_message_creation(self):
        message = ChatMessage.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content='Test message'
        )
        self.assertEqual(message.content, 'Test message')
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.recipient, self.user2)

    def test_message_list_api(self):
        ChatMessage.objects.create(
            sender=self.user1,
            recipient=self.user2,
            content='Test message'
        )
        response = self.client.get(
            f"{reverse('message-list')}?user_id={self.user2.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    async def test_websocket(self):
        application = AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        communicator = WebsocketCommunicator(application, "/ws/chat/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        
        # Test sending message
        await communicator.send_json_to({
            'message': 'Test message',
            'recipient_id': self.user2.id
        })
        
        # Test receiving message
        response = await communicator.receive_json_from()
        self.assertEqual(response['content'], 'Test message')
        
        await communicator.disconnect()

class UserAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')

    def test_user_registration(self):
        response = self.client.post(self.register_url, {
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_user_login(self):
        User.objects.create_user(username='testuser', password='testpass123')
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)