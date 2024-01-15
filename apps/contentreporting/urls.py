from django.urls import path
from . import views

urlpatterns = [
    path('report_post/', views.report_post, name='report_post'),
]
