import os
import tempfile
from datetime import datetime
from io import BytesIO

import cv2
import pillow_heif
import shortuuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import JsonResponse
from PIL import Image
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.mediaposts.models import Media, PetProfile, Post

# TODO: refactor this file


pillow_heif.register_heif_opener()


ALLOWED_IMAGE_TYPES = {'.png', '.jpg', '.jpeg', '.heic'}
ALLOWED_VIDEO_TYPES = {'.mp4', '.mov'}

MAX_IMAGES_PER_POST = 9

MAX_VIDEO_DURATION = 15

MAX_VIDEO_WIDTH = 1080
MAX_VIDEO_HEIGHT = 1080


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

    # Check if the media files are either all images or a single video
    image_files = [file for file in media_files if os.path.splitext(
        file.name.lower())[1] in ALLOWED_IMAGE_TYPES]
    video_files = [file for file in media_files if os.path.splitext(
        file.name.lower())[1] in ALLOWED_VIDEO_TYPES]

    if len(image_files) == len(media_files):
        # All files are images
        if len(image_files) > MAX_IMAGES_PER_POST:
            return JsonResponse({'error': f'Cannot upload more than {MAX_IMAGES_PER_POST} images in a single post'}, status=400)
        media_urls = process_and_upload_images(image_files, pet_profile.pet_id)
    elif len(video_files) == 1 and len(media_files) == 1:
        # Exactly one file, which is a video
        # Assume this function exists
        media_urls = process_and_upload_videos(video_files, pet_profile.pet_id)
    else:
        # Invalid combination of files
        return JsonResponse({'error': 'You can either upload up to 9 images or 1 video'}, status=400)

    if isinstance(media_urls, JsonResponse):
        return media_urls

    # Create post and associated media records
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


def process_and_upload_images(image_files, pet_profile_id):
    converted_media_files = []

    # Convert HEIC to JPEG and process images
    for image_file in image_files:
        if os.path.splitext(image_file.name.lower())[1] == '.heic':
            image = Image.open(image_file)
            image_file = convert_image_to_jpeg(image, image_file.name)

        converted_media_files.append(image_file)

    # Upload processed images
    media_urls = upload_media_to_digital_ocean(
        converted_media_files, pet_profile_id)
    return media_urls


def process_and_upload_videos(video_files, pet_profile_id):
    media_data = []  # This will store dictionaries for each video file
    date_str = datetime.now().strftime('%Y-%m-%d')

    for video_file in video_files:
        # Handle video files without a temporary_file_path
        if hasattr(video_file, 'temporary_file_path'):
            video_file_path = video_file.temporary_file_path()
        else:
            # Create a temporary file for the uploaded video file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.name)[1]) as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)
                video_file_path = temp_file.name

        # Create and upload a thumbnail for the video
        unique_filename = shortuuid.ShortUUID().random(length=8)
        thumbnail_info = create_video_thumbnail(
            video_file_path, pet_profile_id, unique_filename)
        if thumbnail_info is None:
            return JsonResponse({'error': 'Failed to create video thumbnail'}, status=500)

        # Check the video duration
        duration = get_video_duration(video_file_path)
        if duration > MAX_VIDEO_DURATION:
            return JsonResponse({'error': f'Video length exceeds the maximum allowed duration of {MAX_VIDEO_DURATION / 60} minutes'}, status=400)

        # TODO: Add Video Resize Logic

        # Upload the video
        with open(video_file_path, 'rb') as video_to_upload:
            # Ensuring the file is in MP4 format
            new_filename = f"{unique_filename}.mp4"
            file_path = f"{settings.ENV_FOLDER}/media_posts/{pet_profile_id}/{date_str}/{new_filename}"
            default_storage.save(file_path, video_to_upload)
            media_url = default_storage.url(file_path)

        media_item = {
            'media_url': media_url,
            'thumbnail_small_url': thumbnail_info['url']
        }
        media_data.append(media_item)

    return media_data


def create_post_and_media(pet_profile, caption, media_data):
    post = Post.objects.create(pet=pet_profile, caption=caption)
    for index, item in enumerate(media_data):
        Media.objects.create(
            post=post,
            media_url=item['media_url'],
            thumbnail_small_url=item['thumbnail_small_url'],
            media_type=determine_media_type(item['media_url']),
            order=index
        )
    return post

############################### Utilities: Uploading to DO ###############################


def upload_media_to_digital_ocean(media_files, pet_profile_id):
    media_data = []  # This will store dictionaries for each media file
    date_str = datetime.now().strftime('%Y-%m-%d')

    for file in media_files:
        unique_filename = shortuuid.ShortUUID().random(length=8)
        file_extension_with_dot = '.jpg'
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
                'media_url': resized_image_info['url'],
                'thumbnail_small_url': small_thumbnail_info['url']
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


def convert_image_to_jpeg(image, filename):
    buffer = BytesIO()
    new_filename = filename.rsplit('.', 1)[0] + '.jpg'
    image.convert('RGB').save(buffer, 'JPEG')
    buffer.seek(0)
    return InMemoryUploadedFile(buffer, 'ImageField', new_filename, 'image/jpeg', buffer.tell(), None)


def save_and_upload_image(image, file_path, tag):
    buffer = BytesIO()
    image.save(buffer, format='JPEG')
    buffer.seek(0)
    default_storage.save(file_path, buffer)
    media_url = default_storage.url(file_path)
    return {'url': media_url, 'tag': tag}


########################## Utilities: Video Processing ##########################

def get_video_duration(file_path):
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Ensure fps is not zero to avoid division by zero
    duration = frame_count / fps if fps > 0 else 0
    cap.release()
    return duration


def create_video_thumbnail(video_file_path, pet_profile_id, unique_filename):
    # Capture a frame from the video using the file path
    cap = cv2.VideoCapture(video_file_path)  # Use the path directly
    success, frame = cap.read()
    if not success:
        cap.release()
        return None  # Could not read a frame, handle error appropriately

    # Convert the captured frame to a PIL Image
    frame_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    # Resize the image
    thumbnail = resize_image(frame_image, 600)

    # Generate the thumbnail file path
    thumbnail_filename = f"{unique_filename}_thumbnail.jpg"
    date_str = datetime.now().strftime('%Y-%m-%d')
    thumbnail_file_path = f"{settings.ENV_FOLDER}/media_posts/{pet_profile_id}/{date_str}/{thumbnail_filename}"

    # Save and upload the thumbnail
    thumbnail_info = save_and_upload_image(
        thumbnail, thumbnail_file_path, 'thumbnail_small')

    # Make sure to release the video capture object
    cap.release()

    return thumbnail_info


def get_video_resolution(file_path):
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise ValueError("Unable to open the video file.")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return width, height


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
    elif extension in ALLOWED_VIDEO_TYPES:
        return 'video'
    else:
        return 'unknown'
