import os

import boto3
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import DeletedUserLog
from apps.mediaposts.models import Post
from apps.mediaposts.views import delete_media_from_digital_ocean
from apps.petprofiles.models import PetProfile
from apps.petprofiles.views import delete_image_from_do_space

from .utils import get_or_create_user, verify_apple_identity_token

User = get_user_model()


class CheckEmailView(APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        email = request.data.get('email')

        if User.objects.filter(email=email).exists():
            return Response({"isNewUser": False})
        else:
            return Response({"isNewUser": True})


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        reason_detail = request.data.get('reason_detail', '')
        with transaction.atomic():
            user = request.user

            # Log the deletion with provided reason detail
            DeletedUserLog.objects.create(
                # Consider using a different identifier or anonymization method
                anonymized_id=str(user.pk),
                reason_detail=reason_detail
            )

            # Retrieve all posts associated with the user
            user_posts = Post.objects.filter(pet__user=user)

            # Delete associated media from Digital Ocean
            for post in user_posts:
                for media in post.media.all():
                    delete_media_from_digital_ocean(media.media_url)
                    delete_media_from_digital_ocean(media.thumbnail_small_url)

                # After deleting media, delete the post
                post.delete()

            # Initialize boto3 client for Digital Ocean
            session = boto3.session.Session()
            client = session.client(
                's3',
                region_name='sfo3',
                endpoint_url='https://sfo3.digitaloceanspaces.com',
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )

            # Retrieve all pet profiles associated with the user
            user_pet_profiles = PetProfile.objects.filter(user=user)

            # Delete profile pictures from Digital Ocean
            for pet_profile in user_pet_profiles:
                if pet_profile.profile_pic_regular:
                    delete_image_from_do_space(
                        client, pet_profile.profile_pic_regular)
                if pet_profile.profile_pic_thumbnail_small:
                    delete_image_from_do_space(
                        client, pet_profile.profile_pic_thumbnail_small)
                pet_profile.delete()  # Delete the pet profile after its images

            # Now, delete the user
            user.delete()

            # Return a response to indicate successful deletion
            return Response({"message": "User account and all related data have been deleted."}, status=status.HTTP_204_NO_CONTENT)


#  Apple Sign in

@api_view(['POST'])
@permission_classes([AllowAny])
def apple_sign_in(request):
    identity_token = request.data.get('identity_token')
    first_name = request.data.get('first_name')  # Get first name from request
    last_name = request.data.get('last_name')  # Get last name from request

    if not identity_token:
        return JsonResponse({'error': 'Missing identity token'}, status=400)

    try:
        decoded_token = verify_apple_identity_token(identity_token)
        # Pass first_name and last_name to get_or_create_user function
        user = get_or_create_user(decoded_token, first_name, last_name)
        jwt_token = user.generate_jwt()
        return JsonResponse({'token': jwt_token, 'user_id': user.id})
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=403)
