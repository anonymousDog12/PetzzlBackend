from django.urls import path
from .views.create_post_views import create_post_view
from .views.fetch_feed_views import get_feed
from .views.delete_post_views import delete_post
from .views.get_post_views import get_post_media, get_pet_posts

urlpatterns = [
    path('create_post/', create_post_view, name='create_post'),
    path('post_media/<int:post_id>/<str:detail_level>/',
         get_post_media, name='get_post_media'),
    path('feed/', get_feed, name='get_feed'),
    path('delete_post/<int:post_id>/', delete_post, name='delete_post'),
    path('pet_posts/<str:pet_id>/', get_pet_posts, name='get_pet_posts'),
]
