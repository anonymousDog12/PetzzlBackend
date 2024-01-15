from django.urls import path
from .views import CheckEmailView, DeleteAccountView

urlpatterns = [
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
]
