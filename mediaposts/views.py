from django.db import transaction
import boto3
from urllib.parse import urlparse
from .models import Post
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
import os
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import PetProfile, Post, Media

from PIL import Image
from io import BytesIO

import shortuuid
from datetime import datetime


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_post_view(request):
    try:
        pet_id = request.data.get('pet_id')
        pet_profile = validate_pet_profile(pet_id, request.user)
    except PetProfile.DoesNotExist:
        return JsonResponse({'error': 'Pet profile does not exist'}, status=404)
    except PermissionError:
        return JsonResponse({'error': 'User not authorized'}, status=403)

    # Retrieve media files from the request
    media_files = request.FILES.getlist('media_files')
    if not media_files:
        return JsonResponse({'error': 'At least one media file is required'}, status=400)

    # Check if media files are valid images
    for file in media_files:
        if not is_valid_image_type(file.name):
            return JsonResponse({'error': f'Invalid file type for file {file.name}'}, status=400)

    # Process upload if all files are valid
    media_urls = upload_media_to_digital_ocean(media_files, pet_profile.pet_id)
    post = create_post_and_media(
        pet_profile, request.data.get('caption'), media_urls)

    return JsonResponse({'message': 'Post created successfully', 'post_id': post.id}, status=201)


def validate_pet_profile(pet_id, user):
    pet_profile = PetProfile.objects.get(pet_id=pet_id)
    if pet_profile.user != user:
        raise PermissionError
    return pet_profile


def upload_media_to_digital_ocean(media_files, pet_profile_id):
    media_data = []  # This will store dictionaries for each media file
    date_str = datetime.now().strftime('%Y-%m-%d')

    for file in media_files:
        unique_filename = shortuuid.ShortUUID().random(length=8)
        file_extension = file.name.split('.')[-1]
        new_filename = f"{unique_filename}.{file_extension}"
        file_path = f"{settings.ENV_FOLDER}/media_posts/{pet_profile_id}/{date_str}/{new_filename}"

        if file_extension.lower() in ['jpg', 'jpeg', 'png']:
            image = Image.open(file)

            # Resize and upload original size
            resized_image = resize_image(image, 1200)
            resized_path = file_path.replace(
                new_filename, f"{unique_filename}_resized.{file_extension}")
            resized_image_info = save_and_upload_image(
                resized_image, resized_path, 'full_size')

            # Resize and upload medium thumbnail
            medium_thumbnail = resize_image(image, 600)
            medium_path = file_path.replace(
                new_filename, f"{unique_filename}_medium.{file_extension}")
            medium_thumbnail_info = save_and_upload_image(
                medium_thumbnail, medium_path, 'thumbnail_medium')

            # Resize and upload small thumbnail
            small_thumbnail = resize_image(image, 300)
            small_path = file_path.replace(
                new_filename, f"{unique_filename}_small.{file_extension}")
            small_thumbnail_info = save_and_upload_image(
                small_thumbnail, small_path, 'thumbnail_small')

            media_item = {
                'full_size_url': resized_image_info['url'],
                'medium_thumbnail_url': medium_thumbnail_info['url'],
                'small_thumbnail_url': small_thumbnail_info['url']
            }
            media_data.append(media_item)

        else:
            # For non-image files, upload as is
            default_storage.save(file_path, file)
            media_url = default_storage.url(file_path)
            media_item = {
                'full_size_url': media_url,
                'medium_thumbnail_url': '',  # Non-image files won't have thumbnails
                'small_thumbnail_url': ''
            }
            media_data.append(media_item)

    return media_data


def resize_image(image, max_size):
    ratio = max_size / max(image.width, image.height)
    new_size = (int(image.width * ratio), int(image.height * ratio))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def save_and_upload_image(image, file_path, tag):
    buffer = BytesIO()

    # Convert image to JPEG
    if image.format != 'JPEG':
        # Change file extension to .jpg
        file_path = file_path.rsplit('.', 1)[0] + '.jpg'

    # Convert image to RGB mode, necessary for JPEG
    image = image.convert('RGB')
    image.save(buffer, format='JPEG')  # Save image as JPEG
    buffer.seek(0)
    default_storage.save(file_path, buffer)
    media_url = default_storage.url(file_path)
    return {'url': media_url, 'tag': tag}


def create_post_and_media(pet_profile, caption, media_data):
    post = Post.objects.create(pet=pet_profile, caption=caption)
    for index, item in enumerate(media_data):
        Media.objects.create(
            post=post,
            image_url=item['full_size_url'],
            thumbnail_medium_url=item['medium_thumbnail_url'],
            thumbnail_small_url=item['small_thumbnail_url'],
            media_type=determine_media_type(item['full_size_url']),
            order=index
        )
    return post


def determine_media_type(url):
    if url.endswith('.jpg'):
        return 'photo'
    elif url.endswith(('.mp4', '.mov')):
        return 'video'
    else:
        return 'unknown'  # or raise an exception


def is_valid_image_type(filename):
    allowed_image_extensions = {'.png', '.jpg', '.jpeg'}
    extension = os.path.splitext(filename.lower())[1]
    return extension in allowed_image_extensions


def is_valid_media_type(filename):
    allowed_image_extensions = {'.png', '.jpg', '.jpeg'}
    allowed_video_extensions = {'.mp4', '.mov'}
    extension = os.path.splitext(filename.lower())[1]
    if extension in allowed_image_extensions or extension in allowed_video_extensions:
        return True
    return False


#######################################


@api_view(['GET'])
@permission_classes([AllowAny])
def get_post_media(request, post_id, detail_level='overview'):
    post = get_object_or_404(Post, pk=post_id)
    media_data = []

    # TODO: make detail levels global constants
    if detail_level == 'overview':
        first_media = post.media.first()  # Get the first media item
        if first_media:
            media_data.append({
                'media_id': first_media.id,
                'thumbnail_url': first_media.thumbnail_medium_url
            })
    elif detail_level == 'full':
        for media in post.media.all():
            media_data.append({
                'media_id': media.id,
                'full_size_url': media.image_url,
                # Add other media details here
            })

    response_data = {
        'post_id': post.id,
        'caption': post.caption,
        'media': media_data,
        # Add other post details here
    }

    return Response(response_data)


################## Post Deletion ####################


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_post_view(request, post_id):
    try:
        # Retrieve the post and verify that the request user is the owner
        post = Post.objects.get(id=post_id, pet__user=request.user)
    except Post.DoesNotExist:
        return Response({'error': 'Post not found or not authorized to delete'}, status=404)

    with transaction.atomic():
        # Delete media files from Digital Ocean
        for media in post.media.all():
            delete_media_from_digital_ocean(media.image_url)
            delete_media_from_digital_ocean(media.thumbnail_medium_url)
            delete_media_from_digital_ocean(media.thumbnail_small_url)

        post.delete()

    return Response({'message': 'Post deleted successfully'}, status=200)


def delete_media_from_digital_ocean(url):
    if url:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.lstrip('/').split('/')
        bucket_name = path_parts[0]
        object_name = '/'.join(path_parts[1:])

        # Set up boto3 client with Digital Ocean Spaces credentials
        client = boto3.client('s3',
                              region_name='sfo3',  # Replace with your region if different
                              # Replace with your endpoint URL if different
                              endpoint_url='https://sfo3.digitaloceanspaces.com',
                              aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                              aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

        try:
            client.delete_object(Bucket=bucket_name, Key=object_name)
            print(f"Successfully deleted {object_name} from {bucket_name}")
        except Exception as e:
            print(
                f"Failed to delete {object_name} from {bucket_name}. Error: {e}")
