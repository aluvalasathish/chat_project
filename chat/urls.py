from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('api/users/', views.UserListView.as_view(), name='user-list'),
    path('api/messages/', views.ChatMessageListView.as_view(), name='message-list'),
]