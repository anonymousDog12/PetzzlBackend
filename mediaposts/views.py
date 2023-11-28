from datetime import datetime
import shortuuid
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
import pillow_heif
import cv2


pillow_heif.register_heif_opener()

# TODO: allow max number of images to be 9 in a single post

ALLOWED_IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.heic'}
ALLOWED_VIDEO_TYPES = {'.mp4', '.mov'}

MAX_IMAGES_PER_POST = 9

MAX_VIDEO_LENGTH = 30
MAX_VIDEO_WIDTH = 1200
MAX_VIDEO_HEIGHT = 1200


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

    image_count = sum(1 for file in media_files if os.path.splitext(
        file.name.lower())[1] in ALLOWED_IMAGE_TYPES)
    video_count = sum(1 for file in media_files if os.path.splitext(
        file.name.lower())[1] in ALLOWED_VIDEO_TYPES)

    if image_count > MAX_IMAGES_PER_POST:
        return JsonResponse({'error': f'Cannot upload more than {MAX_IMAGES_PER_POST} images in a single post'}, status=400)

    if video_count > 1 or (video_count == 1 and image_count > 0):
        return JsonResponse({'error': 'Only multiple images or a single video can be uploaded in one post'}, status=400)

    media_urls = upload_media_to_digital_ocean(media_files, pet_profile.pet_id)
    # Check if media_urls is a JsonResponse (error case)
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


def validate_pet_profile(pet_id, user):
    pet_profile = PetProfile.objects.get(pet_id=pet_id)
    if pet_profile.user != user:
        raise PermissionError
    return pet_profile


def get_video_duration(file):
    # Read video file directly from the uploaded file in memory
    cap = cv2.VideoCapture(file.temporary_file_path())
    fps = cap.get(cv2.CAP_PROP_FPS)  # Frames per second
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps

    cap.release()
    return duration


def get_video_resolution(file):
    # Read video file directly from the uploaded file in memory
    cap = cv2.VideoCapture(file.temporary_file_path())

    if not cap.isOpened():
        raise ValueError("Unable to open the video file.")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    cap.release()
    return width, height


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

            # Resize and upload medium thumbnail
            medium_thumbnail = resize_image(image, 600)
            medium_path = file_path.replace(
                new_filename, f"{unique_filename}_medium{file_extension_with_dot}")
            medium_thumbnail_info = save_and_upload_image(
                medium_thumbnail, medium_path, 'thumbnail_medium')

            # Resize and upload small thumbnail
            small_thumbnail = resize_image(image, 300)
            small_path = file_path.replace(
                new_filename, f"{unique_filename}_small{file_extension_with_dot}")
            small_thumbnail_info = save_and_upload_image(
                small_thumbnail, small_path, 'thumbnail_small')

            media_item = {
                'full_size_url': resized_image_info['url'],
                'medium_thumbnail_url': medium_thumbnail_info['url'],
                'small_thumbnail_url': small_thumbnail_info['url']
            }
            media_data.append(media_item)

        elif file_extension_with_dot in ALLOWED_VIDEO_TYPES:
            if get_video_duration(file) > MAX_VIDEO_LENGTH:
                return JsonResponse({'error': 'Video length exceeds the allowed limit'}, status=400)

            width, height = get_video_resolution(file)
            if width > MAX_VIDEO_WIDTH or height > MAX_VIDEO_HEIGHT:
                # Process the file for resizing
                temp_output_path = "temp_resized_video.mp4"
                resize_video(file.temporary_file_path(),
                             temp_output_path, MAX_VIDEO_WIDTH, MAX_VIDEO_HEIGHT)
                file_to_upload = open(temp_output_path, 'rb')
            else:
                file_to_upload = file

            # Upload video file (resized or original)
            default_storage.save(file_path, file_to_upload)
            media_url = default_storage.url(file_path)
            media_data.append({
                'full_size_url': media_url,
                'medium_thumbnail_url': None,
                'small_thumbnail_url': None
            })

            if 'temp_resized_video.mp4' in locals():
                file_to_upload.close()
                os.remove(temp_output_path)

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


def resize_video(input_path, output_path, max_width, max_height):
    # Capture the video
    cap = cv2.VideoCapture(input_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Define the codec

    # Get original video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Calculate new dimensions
    scaling_factor = min(max_width/width, max_height/height)
    new_width = int(width * scaling_factor)
    new_height = int(height * scaling_factor)

    # Video writer to save the resized video
    out = cv2.VideoWriter(output_path, fourcc, fps, (new_width, new_height))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize the frame
        resized_frame = cv2.resize(
            frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        out.write(resized_frame)

    # Release resources
    cap.release()
    out.release()


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
            media_url=item['full_size_url'],
            thumbnail_medium_url=item['medium_thumbnail_url'],
            thumbnail_small_url=item['small_thumbnail_url'],
            media_type=determine_media_type(item['full_size_url']),
            order=index
        )
    return post


def determine_media_type(url):
    extension = os.path.splitext(url.lower())[1]
    if extension in ALLOWED_IMAGE_TYPES:
        return 'photo'
    elif extension in ALLOWED_VIDEO_TYPES:
        return 'video'
    else:
        return 'unknown'  # or raise an exception


def is_valid_image_type(filename):
    extension = os.path.splitext(filename.lower())[1]
    return extension in ALLOWED_IMAGE_TYPES


def is_valid_media_type(filename):
    extension = os.path.splitext(filename.lower())[1]
    if extension in ALLOWED_IMAGE_TYPES or extension in ALLOWED_VIDEO_TYPES:
        return True
    return False

###################### FETCH FEED ######################

# TODO: Enhance feed content


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_feed(request):
    # Fetch the latest post made by the user
    user_latest_post = Post.objects.filter(
        pet__user=request.user).order_by('-created_at').first()

    # Fetch additional posts from other users
    other_posts = Post.objects.exclude(
        pet__user=request.user).order_by('-created_at')[:10]  # Fetch 10 other posts

    feed = []
    if user_latest_post:
        feed.append(convert_post_to_response_format(user_latest_post))

    for post in other_posts:
        feed.append(convert_post_to_response_format(post))

    return Response(feed)


def convert_post_to_response_format(post):
    media_data = [{
        'media_id': media.id,
        'full_size_url': media.media_url,
        'thumbnail_medium_url': media.thumbnail_medium_url,
        # Add other media details here
    } for media in post.media.all()]

    return {
        'post_id': post.id,
        'caption': post.caption,
        'media': media_data,
        # Add other post details here
    }

###################### GET POST ######################


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
                'full_size_url': media.media_url,
                # Add other media details here
            })

    response_data = {
        'post_id': post.id,
        'caption': post.caption,
        'media': media_data,
        # Add other post details here
    }

    return Response(response_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_pet_posts(request, pet_id):
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
            delete_media_from_digital_ocean(media.media_url)
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
