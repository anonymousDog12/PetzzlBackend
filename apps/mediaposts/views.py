import os
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

import boto3
import pillow_heif
import shortuuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from google.cloud import vision_v1
from PIL import Image
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.userblocking.models import BlockedUser

from .models import Media, PetProfile, Post

# TODO: refactor this file


pillow_heif.register_heif_opener()


ALLOWED_IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.heic'}

MAX_IMAGES_PER_POST = 9

############################### CREATE POST ###############################


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

    media_files = request.FILES.getlist('media_files')
    if not media_files:
        return JsonResponse({'error': 'At least one media file is required'}, status=400)

    # First, validate file format
    for media_file in media_files:
        if os.path.splitext(media_file.name.lower())[1] not in ALLOWED_IMAGE_TYPES:
            return JsonResponse({'error': f'Unsupported file type: {os.path.splitext(media_file.name.lower())[1]}'}, status=400)

    if len(media_files) > MAX_IMAGES_PER_POST:
        return JsonResponse({'error': f'Cannot upload more than {MAX_IMAGES_PER_POST} images in a single post'}, status=400)

    # Then, perform content policy check
    for media_file in media_files:
        if not is_suitable_pet_image_in_memory(media_file):
            return JsonResponse({
                'error': 'Content policy violation',
                'error_type': 'inappropriate_content',
                'message': 'Our AI filter spotted something that might not meet our content guidelines. Please review and try again. If this seems mistaken, please contact admin@petzzl.app for help.',
            }, status=400)

    # After validation, continue to upload and create post
    media_urls = upload_media_to_digital_ocean(media_files, pet_profile.pet_id)
    if isinstance(media_urls, JsonResponse):
        return media_urls

    post = create_post_and_media(
        pet_profile, request.data.get('caption'), media_urls)

    first_media = post.media.first()
    media_url = first_media.media_url if first_media else None
    thumbnail_small_url = first_media.thumbnail_small_url if first_media else None

    return JsonResponse({
        'message': 'Post created successfully',
        'post_id': post.id,
        'media_url': media_url,
        'thumbnail_small_url': thumbnail_small_url
    }, status=201)


def create_post_and_media(pet_profile, caption, media_data):
    post = Post.objects.create(pet=pet_profile, caption=caption)
    for index, item in enumerate(media_data):
        Media.objects.create(
            post=post,
            media_url=item['full_size_url'],
            thumbnail_small_url=item['small_thumbnail_url'],
            media_type=determine_media_type(item['full_size_url']),
            order=index
        )
    return post

############################### Utilities: Uploading to DO ###############################


def upload_media_to_digital_ocean(media_files, pet_profile_id):
    media_data = []  # This will store dictionaries for each media file
    date_str = datetime.now().strftime('%Y-%m-%d')

    for file in media_files:
        unique_filename = shortuuid.ShortUUID().random(length=8)
        file_extension_with_dot = os.path.splitext(file.name.lower())[1]
        new_filename = f"{unique_filename}{file_extension_with_dot}"
        file_path = f"{settings.ENV_FOLDER}/media_posts/{pet_profile_id}/{date_str}/{new_filename}"

        if file_extension_with_dot in ALLOWED_IMAGE_TYPES:
            image = Image.open(file)

            # Resize and upload original size
            resized_image = resize_image(image, 1200)
            resized_path = file_path.replace(
                new_filename, f"{unique_filename}_resized{file_extension_with_dot}")
            resized_image_info = save_and_upload_image(
                resized_image, resized_path, 'full_size')

            # Resize and upload small thumbnail
            small_thumbnail = resize_image(image, 300)
            small_path = file_path.replace(
                new_filename, f"{unique_filename}_small{file_extension_with_dot}")
            small_thumbnail_info = save_and_upload_image(
                small_thumbnail, small_path, 'thumbnail_small')

            media_item = {
                'full_size_url': resized_image_info['url'],
                'small_thumbnail_url': small_thumbnail_info['url']
            }
            media_data.append(media_item)

        else:
            return JsonResponse({'error': f'Unsupported file type: {file_extension_with_dot}'}, status=400)

    return media_data


########################## Utilities: Image Processing ##########################

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

########################## Utilities: Image Filtering ##########################


def is_suitable_pet_image_in_memory(image_file, confidence_threshold=0.5):
    client = vision_v1.ImageAnnotatorClient()

    content = image_file.read()
    image = vision_v1.Image(content=content)

    response_labels = client.label_detection(image=image)
    labels = response_labels.label_annotations
    pet_related_terms = ['pet', 'dog', 'cat', 'animal', 'horse', 'turtle',
                         'bird', 'fish', 'hamster', 'rabbit', 'reptile']
    is_animal = False

    for label in labels:
        if label.description.lower() in pet_related_terms and label.score >= confidence_threshold:
            is_animal = True
            break

    if is_animal:
        response_safe_search = client.safe_search_detection(image=image)
        safe = response_safe_search.safe_search_annotation
        thresholds = {
            'adult': vision_v1.Likelihood.POSSIBLE,
            'violence': vision_v1.Likelihood.POSSIBLE
        }

        if safe.adult < thresholds['adult'] and safe.violence < thresholds['violence']:
            return True

    return False


############################### FETCH FEED ###############################

# TODO: Enhance feed content


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_feed(request):
    paginator = PageNumberPagination()
    paginator.page_size = 5

    # Fetch IDs of users who have blocked the current user
    blocked_by_others_ids = BlockedUser.objects.filter(
        blocked=request.user
    ).values_list('blocker_id', flat=True)

    # Fetch IDs of users who are blocked by the current user
    blocked_by_user_ids = BlockedUser.objects.filter(
        blocker=request.user
    ).values_list('blocked_id', flat=True)

    # Combine both lists of IDs
    all_blocked_users_ids = set(
        list(blocked_by_others_ids) + list(blocked_by_user_ids))

    # Fetch all posts, excluding those from pet profiles owned by any of the blocked users
    all_posts = Post.objects.exclude(
        pet__user_id__in=all_blocked_users_ids
    ).order_by('-created_at')

    # Apply pagination to the queryset
    paginated_posts = paginator.paginate_queryset(all_posts, request)

    # Convert posts to the response format
    feed = [convert_post_to_response_format(post) for post in paginated_posts]

    return paginator.get_paginated_response(feed)


def convert_post_to_response_format(post):
    media_data = [{
        'media_id': media.id,
        'full_size_url': media.media_url,
    } for media in post.media.all()]

    pet_profile_pic_url = post.pet.profile_pic_thumbnail_small
    pet_id = post.pet.pet_id
    pet_type = post.pet.pet_type

    # Format the created_at date to a string (e.g., 'YYYY-MM-DD')
    created_at_str = post.created_at.strftime('%Y-%m-%d')

    return {
        'post_id': post.id,
        'caption': post.caption,
        'media': media_data,
        'pet_id': pet_id,
        'pet_profile_pic': pet_profile_pic_url,
        'pet_type': pet_type,  # Include pet type
        'posted_date': created_at_str  # Include the post creation date
    }


############################### GET POST ###############################


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_post_media(request, post_id, detail_level='overview'):
    post = get_object_or_404(Post, pk=post_id)

    # Check if the current user is blocked by or has blocked the pet's owner
    blocked_users = set(BlockedUser.objects.filter(
        blocker=request.user).values_list('blocked', flat=True))
    users_blocking = set(BlockedUser.objects.filter(
        blocked=request.user).values_list('blocker', flat=True))

    if post.pet.user.id in blocked_users or post.pet.user.id in users_blocking:
        # No full post details should be shown if the user is blocked or is blocking
        return Response({'message': 'Access denied'}, status=403)

    media_data = []
    # Format the created_at date to a string (e.g., 'YYYY-MM-DD')
    created_at_str = post.created_at.strftime('%Y-%m-%d')

    # TODO: make detail levels global constants
    if detail_level == 'full':
        for media in post.media.all():
            media_data.append({
                'media_id': media.id,
                'full_size_url': media.media_url,
            })

    response_data = {
        'post_id': post.id,
        'caption': post.caption,
        'media': media_data,
        'posted_date': created_at_str,  # Include the post creation date
    }

    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pet_posts(request, pet_id):
    # Fetch the pet profile
    pet = PetProfile.objects.filter(
        pet_id=pet_id).select_related('user').first()
    if not pet:
        return Response({'message': 'Pet profile not found'}, status=404)

    user = request.user
    # Fetch sets of users who have been blocked or have blocked the current user
    blocked_users = set(BlockedUser.objects.filter(
        blocker=user).values_list('blocked', flat=True))
    users_blocking = set(BlockedUser.objects.filter(
        blocked=user).values_list('blocker', flat=True))

    # Combine the sets to check if there is a block in either direction
    if pet.user.id in blocked_users or pet.user.id in users_blocking:
        # No posts should be shown if the user is blocked or is blocking
        return Response([])

    # Fetch all posts for a given pet profile
    pet_posts = Post.objects.filter(pet_id=pet_id).order_by('-created_at')

    response_data = []
    for post in pet_posts:
        first_media = post.media.first()  # Get the first media item
        if first_media:
            post_data = {
                'post_id': post.id,
                'caption': post.caption,
                'thumbnail_url': first_media.thumbnail_small_url
                # Add any other necessary post details
            }
            response_data.append(post_data)

    return Response(response_data)

############################### POST DELETION ###############################


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
            delete_media_from_digital_ocean(media.media_url)
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


############################### Utility Functions ###############################


def validate_pet_profile(pet_id, user):
    pet_profile = PetProfile.objects.get(pet_id=pet_id)
    if pet_profile.user != user:
        raise PermissionError
    return pet_profile


def determine_media_type(url):
    extension = os.path.splitext(url.lower())[1]
    if extension in ALLOWED_IMAGE_TYPES:
        return 'photo'
    else:
        return 'unknown'  # or raise an exception
