from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import ChatMessage, UserActivity
from .serializers import UserSerializer, ChatMessageSerializer
from django.db import models
from django.utils import timezone

@login_required
def chat_view(request):
    # Update current user's activity
    activity, _ = UserActivity.objects.get_or_create(user=request.user)
    activity.update_activity()

    # Get all users except current user with their activity status
    users = User.objects.exclude(id=request.user.id).select_related('useractivity')
    
    # Create a list of user data including activity status
    user_data = []
    for user in users:
        try:
            is_active = user.useractivity.is_active_now
            last_seen = user.useractivity.last_activity
        except UserActivity.DoesNotExist:
            is_active = False
            last_seen = None
        
        user_data.append({
            'user': user,
            'is_active': is_active,
            'last_seen': last_seen
        })

    return render(request, 'chat/chat.html', {'users': user_data})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Set user as online
                activity, _ = UserActivity.objects.get_or_create(user=user)
                activity.update_activity()
                return redirect('chat')
    else:
        form = AuthenticationForm()
    return render(request, 'chat/login.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        # Set user as offline
        try:
            activity = UserActivity.objects.get(user=request.user)
            activity.is_online = False
            activity.save()
        except UserActivity.DoesNotExist:
            pass
    logout(request)
    return redirect('login')

def register(request):
    if request.user.is_authenticated:
        return redirect('chat')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            # Create activity record for new user
            UserActivity.objects.create(user=user, is_online=True)
            return redirect('chat')
    else:
        form = UserCreationForm()
    return render(request, 'chat/register.html', {'form': form})

class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.exclude(id=self.request.user.id).select_related('useractivity')

class ChatMessageListView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        other_user_id = self.request.query_params.get('user_id')
        if other_user_id:
            return ChatMessage.objects.filter(
                (models.Q(sender=self.request.user, recipient_id=other_user_id) |
                 models.Q(sender_id=other_user_id, recipient=self.request.user))
            ).order_by('timestamp')