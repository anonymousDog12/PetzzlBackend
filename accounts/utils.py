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

    return user
