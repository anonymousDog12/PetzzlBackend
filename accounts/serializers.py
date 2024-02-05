from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer

from .utils import add_subscriber_to_mailchimp

User = get_user_model()


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = '__all__'

    def save(self, **kwargs):
        user = super().save(**kwargs)  # Save the user instance

        # Add the user to Mailchimp
        try:
            add_subscriber_to_mailchimp(
                user.email, user.first_name, user.last_name)
        except Exception as e:
            # Send an email to admin if something goes wrong
            subject = "Mailchimp Subscription Error"
            message = f"Failed to add subscriber {user.email} to Mailchimp: {e}"
            email_from = settings.DEFAULT_FROM_EMAIL
            recipient_list = ['admin@petzzl.app']
            send_mail(subject, message, email_from, recipient_list)

        return user
