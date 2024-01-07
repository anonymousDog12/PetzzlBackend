from django.urls import path
from . import views

urlpatterns = [
    path('block/', views.block_user, name='block_user'),
    path('unblock/', views.unblock_user, name='unblock_user'),
]
