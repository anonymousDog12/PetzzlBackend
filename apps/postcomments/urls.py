from django.urls import path

from . import views

urlpatterns = [
    path('add_comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path('delete_comment/<int:comment_id>/',
         views.delete_comment, name='delete_comment'),
    path('comments/view/<int:post_id>/',
         views.view_comments_for_post, name='view_comments_for_post'),
]
