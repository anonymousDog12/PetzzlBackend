import os
from io import BytesIO
from urllib.parse import urlparse

import boto3
import shortuuid
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.shortcuts import get_object_or_404
from PIL import Image
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.mediaposts.models import Post
from apps.mediaposts.views import delete_media_from_digital_ocean

from .models import PetProfile
from .serializers import PetProfileSerializer

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def pet_profile_list_create(request):
    if request.method == 'GET':
        pets = PetProfile.objects.all()
        serializer = PetProfileSerializer(pets, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PetProfileSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def pet_profile_detail(request, pet_id):
    pet_profile = get_object_or_404(PetProfile, pet_id=pet_id)

    if request.method == 'GET':
        serializer = PetProfileSerializer(pet_profile)
        return Response(serializer.data)

    if request.user and request.user.is_authenticated:
        if request.method == 'PUT':
            if pet_profile.user == request.user:
                serializer = PetProfileSerializer(
                    pet_profile, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "You do not have permission to edit this pet profile."}, status=status.HTTP_403_FORBIDDEN)

        elif request.method == 'DELETE':
            if pet_profile.user == request.user:
                pet_profile.delete()
                return Response({"message": "Pet Profile has been deleted."})
            else:
                return Response({"message": "You do not have permission to delete this pet profile."}, status=status.HTTP_403_FORBIDDEN)
    else:
        return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_pet_profile(request, pet_id):
    try:
        pet_profile = PetProfile.objects.get(pet_id=pet_id, user=request.user)
    except PetProfile.DoesNotExist:
        return Response({'error': 'Pet profile not found or not authorized to delete'}, status=404)

    with transaction.atomic():
        # Delete profile pictures from Digital Ocean
        if pet_profile.profile_pic_regular:
            delete_media_from_digital_ocean(pet_profile.profile_pic_regular)
        if pet_profile.profile_pic_thumbnail_small:
            delete_media_from_digital_ocean(
                pet_profile.profile_pic_thumbnail_small)

        # Delete all related media posts
        posts = Post.objects.filter(pet=pet_profile)
        for post in posts:
            for media in post.media.all():
                delete_media_from_digital_ocean(media.media_url)
                delete_media_from_digital_ocean(media.thumbnail_small_url)
            post.delete()

        # Now that all related media files are deleted, we can delete the pet profile
        pet_profile.delete()

    return Response({'message': 'Pet profile and related media have been deleted successfully'}, status=200)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_pets_by_user(request, user_id):
    try:
        pets = PetProfile.objects.filter(user_id=user_id)
        if not pets.exists():
            return Response([], status=status.HTTP_200_OK)

        serializer = PetProfileSerializer(pets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except ObjectDoesNotExist:
        return Response({"message": "User not found."}, status=status.HTTP_404_NOT_FOUND)

############################## Pet ID Uniqueness Check ##############################


@api_view(['GET'])
@permission_classes([AllowAny])
# Add pet_id as an argument to the view
def check_pet_id_uniqueness(request, pet_id):
    if pet_id:
        is_unique = not PetProfile.objects.filter(pet_id=pet_id).exists()
        return Response({'is_unique': is_unique})
    else:
        return Response({'error': 'pet_id parameter not provided'}, status=400)


############################## Image Pre-Processing ##############################


def resize_image(image, size):
    """
    Resize the image to the specified size while maintaining aspect ratio.
    """
    img = Image.open(image)
    aspect_ratio = img.width / img.height

    if img.width > img.height:
        width = size
        height = int(size / aspect_ratio)
    else:
        height = size
        width = int(size * aspect_ratio)

    img = img.resize((width, height), Image.LANCZOS)
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    img_content = buffer.getvalue()

    # Change the file extension to .jpg
    base_name, _ = os.path.splitext(image.name)
    new_name = f"{base_name}.jpg"

    return ContentFile(img_content, new_name)


def save_resized_image(image, size, pet_id, unique_name):
    """
    Save the resized image and return its URL.
    """
    resized_image = resize_image(image, size)

    path = f"{settings.PROFILE_PIC_LOCATION}/{pet_id}/{size}_{unique_name}.jpg"
    filename = default_storage.save(path, resized_image)

    return default_storage.url(filename)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_profile_pic(request):
    if request.method == 'POST':
        file = request.FILES['file']
        if not allowed_file(file.name):
            return Response({'error': 'File extension not allowed'}, status=status.HTTP_400_BAD_REQUEST)

        #  TODO: Add checks making sure user is the owner
        pet_id = request.data.get('pet_id', None)

        # Initialize boto3 client for Digital Ocean
        session = boto3.session.Session()
        client = session.client('s3',
                                region_name='sfo3',
                                endpoint_url='https://sfo3.digitaloceanspaces.com',
                                aws_access_key_id=os.getenv(
                                    'AWS_ACCESS_KEY_ID'),
                                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

        # If pet profile has existing images, delete them first.
        pet_profile = PetProfile.objects.get(pet_id=pet_id)
        if pet_profile.profile_pic_regular:
            delete_image_from_do_space(client, pet_profile.profile_pic_regular)
        if pet_profile.profile_pic_thumbnail_small:
            delete_image_from_do_space(
                client, pet_profile.profile_pic_thumbnail_small)

        # Upload new images
        common_unique_name = shortuuid.ShortUUID().random(length=8)

        regular_url = save_resized_image(
            file, 512, str(pet_id), common_unique_name)
        thumbnail_url = save_resized_image(
            file, 100, str(pet_id), common_unique_name)

        # Update the PetProfile model with the new URLs
        pet_profile.profile_pic_regular = regular_url
        pet_profile.profile_pic_thumbnail_small = thumbnail_url
        pet_profile.save()

        return Response({'regular_url': regular_url, 'thumbnail_url': thumbnail_url})

    return Response({'error': 'Invalid request method'}, status=400)


def delete_image_from_do_space(session, url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.lstrip('/').split('/')
    bucket_name = path_parts[0]
    object_name = '/'.join(path_parts[1:])

    try:
        session.delete_object(Bucket=bucket_name, Key=object_name)
        print(f"Successfully deleted {object_name} from {bucket_name}")
    except Exception as e:
        print(f"Failed to delete {object_name} from {bucket_name}. Error: {e}")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_profile_picture(request):
    pet_id = request.data.get('pet_id', None)
    if not pet_id:
        return Response({'error': 'Pet ID is required'}, status=400)

    try:
        pet_profile = PetProfile.objects.get(pet_id=pet_id)
    except PetProfile.DoesNotExist:
        return Response({'error': 'Pet profile does not exist'}, status=404)

    if pet_profile.user != request.user:
        return Response({'error': "You don't have permission to delete this pet profile picture"}, status=403)

    # Initialize boto3 client
    session = boto3.session.Session()
    client = session.client('s3',
                            region_name='sfo3',
                            endpoint_url='https://sfo3.digitaloceanspaces.com',
                            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

    # Delete existing image URLs from Digital Ocean
    if pet_profile.profile_pic_regular:
        delete_image_from_do_space(client, pet_profile.profile_pic_regular)

    if pet_profile.profile_pic_thumbnail_small:
        delete_image_from_do_space(
            client, pet_profile.profile_pic_thumbnail_small)

    # Delete existing image URLs from the database
    pet_profile.profile_pic_regular = None
    pet_profile.profile_pic_thumbnail_small = None
    pet_profile.save()

    return Response({'message': 'Profile pictures deleted successfully'})
