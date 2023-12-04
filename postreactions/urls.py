from django.urls import path
from .views import like_post, unlike_post

urlpatterns = [
    path('posts/<int:post_id>/like/<int:pet_profile_id>/',
         like_post, name='like_post'),
    path('posts/<int:post_id>/unlike/<int:pet_profile_id>/',
         unlike_post, name='unlike_post'),
]
