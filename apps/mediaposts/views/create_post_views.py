import os
from datetime import datetime
from io import BytesIO

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

    converted_media_files = []

    # Validate file format and convert if necessary
    for media_file in media_files:
        file_extension = os.path.splitext(media_file.name.lower())[1]
        if file_extension not in ALLOWED_IMAGE_TYPES:
            return JsonResponse({'error': f'Unsupported file type: {file_extension}'}, status=400)

        # Convert HEIC to JPEG
        if file_extension == '.heic':
            image = Image.open(media_file)
            media_file = convert_image_to_jpeg(image, media_file.name)

        converted_media_files.append(media_file)

    if len(converted_media_files) > MAX_IMAGES_PER_POST:
        return JsonResponse({'error': f'Cannot upload more than {MAX_IMAGES_PER_POST} images in a single post'}, status=400)

    # After validation, continue to upload and create post
    media_urls = upload_media_to_digital_ocean(
        converted_media_files, pet_profile.pet_id)
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
