from django.urls import path
from .views import CheckEmailView, DeleteAccountView, apple_sign_in

urlpatterns = [
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('apple-sign-in/', apple_sign_in, name='apple-sign-in'),
]
