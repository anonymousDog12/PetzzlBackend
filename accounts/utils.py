import jwt
import requests
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()


def verify_apple_identity_token(token):
    # Fetch Apple's public keys
    apple_keys_response = requests.get('https://appleid.apple.com/auth/keys')
    apple_public_keys = apple_keys_response.json()['keys']

    for key in apple_public_keys:
        try:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            decoded_token = jwt.decode(token, public_key, algorithms='RS256',
                                       audience=settings.APPLE_CLIENT_ID, issuer='https://appleid.apple.com')
            return decoded_token
        except jwt.PyJWTError as e:
            # Log the specific error
            print(f"Token verification failed with error: {e}")
    raise ValueError('Token verification failed')


def get_or_create_user(user_data, first_name=None, last_name=None):
    """Get or create a user based on the decoded token data and provided names"""
    email = user_data.get('email')

    if not email:
        raise ValueError('Email is required')

    # Use provided first_name and last_name if available, otherwise fallback to defaults
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'first_name': first_name or user_data.get('given_name', ''),
            'last_name': last_name or user_data.get('family_name', '')
        }
    )

    return user, created


def add_subscriber_to_mailchimp(email, first_name, last_name):
    # Only proceed if in the PROD environment
    if settings.ENV == 'PROD':
        url = f'https://us9.api.mailchimp.com/3.0/lists/{settings.MAILCHIMP_LIST_ID}/members/'
        data = {
            'email_address': email,
            'status': 'subscribed',
            'merge_fields': {
                'FNAME': first_name,
                'LNAME': last_name,
            },
        }
        headers = {
            'Authorization': f'Bearer {settings.MAILCHIMP_API_KEY}',
            'Content-Type': 'application/json'
        }

        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 200:
            # Handle failure: log it, send a notification, etc.
            print(
                f"Failed to add subscriber {email} to Mailchimp: {response.json()}")
    else:
        # Optionally log that the function was called in a non-prod environment
        print(
            f"Skipped adding subscriber {email} to Mailchimp since environment is not PROD.")
