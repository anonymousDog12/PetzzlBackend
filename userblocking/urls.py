from django.urls import path
from . import views

urlpatterns = [
    path('block/', views.block_user, name='block_user'),
    path('unblock/', views.unblock_user, name='unblock_user'),
    path('blocked_profiles/', views.get_blocked_profiles,
         name='get_blocked_profiles'),
]
