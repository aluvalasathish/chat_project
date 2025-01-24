from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from urllib.parse import parse_qs
from django.utils import timezone
from .models import UserActivity

class ChatMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Add any custom view processing here
        pass

    def process_exception(self, request, exception):
        # Log the error and show a user-friendly message
        messages.error(request, "An error occurred. Please try again later.")
        return redirect('chat')

class QueryAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()
        
        if scope["user"].is_authenticated:
            return await super().__call__(scope, receive, send)

        # Handle WebSocket connections
        if scope["type"] == "websocket":
            # Close connection if user is not authenticated
            if isinstance(scope["user"], AnonymousUser):
                return None
        
        return await super().__call__(scope, receive, send)

def QueryAuthMiddlewareStack(inner):
    return QueryAuthMiddleware(AuthMiddlewareStack(inner))

class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Get or create user activity
            activity, created = UserActivity.objects.get_or_create(user=request.user)
            activity.update_activity()

        response = self.get_response(request)
        return response