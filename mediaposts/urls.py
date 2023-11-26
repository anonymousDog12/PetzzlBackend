from django.urls import path
from . import views

urlpatterns = [
    path('create_post/', views.create_post_view, name='create_post'),
    path('post_media/<int:post_id>/<str:detail_level>/',
         views.get_post_media, name='get_post_media'),
    path('feed/', views.get_feed, name='get_feed'),
    path('delete_post/<int:post_id>/',
         views.delete_post_view, name='delete_post'),
    path('pet_posts/<str:pet_id>/', views.get_pet_posts, name='get_pet_posts'),
]
