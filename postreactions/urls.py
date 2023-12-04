from django.urls import path
from .views import check_like_status, get_like_count, like_post, unlike_post

urlpatterns = [
    path('posts/<int:post_id>/like/<int:pet_profile_id>/',
         like_post, name='like_post'),
    path('posts/<int:post_id>/unlike/<int:pet_profile_id>/',
         unlike_post, name='unlike_post'),
    path('posts/<int:post_id>/likecount/',
         get_like_count, name='get_like_count'),
    path('posts/<int:post_id>/likestatus/<int:pet_profile_id>/',
         check_like_status, name='check_like_status'),
]
