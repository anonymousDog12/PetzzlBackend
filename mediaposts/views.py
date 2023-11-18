import os
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import PetProfile, Post, Media

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

    # Validate file types before processing uploads
    for file in media_files:
        if not is_valid_media_type(file.name):
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
    media_urls = []
    date_str = datetime.now().strftime('%Y-%m-%d')
    for file in media_files:
        # Generate a short uuid
        unique_filename = shortuuid.ShortUUID().random(length=8)
        # Extract the file extension and append it to the UUID
        file_extension = file.name.split('.')[-1]
        new_filename = f"{unique_filename}.{file_extension}"
        # Update the file path structure
        file_path = f"{settings.ENV_FOLDER}/media_posts/{pet_profile_id}/{date_str}/{new_filename}"
        default_storage.save(file_path, file)
        media_url = default_storage.url(file_path)
        media_urls.append(media_url)
    return media_urls


def create_post_and_media(pet_profile, caption, media_urls):
    post = Post.objects.create(pet=pet_profile, caption=caption)
    for index, url in enumerate(media_urls):
        Media.objects.create(post=post, image_url=url,
                             media_type=determine_media_type(url), order=index)
    return post


# TODO: refactor the following two functions to avoid repetition


def determine_media_type(url):
    if url.lower().endswith(('.png', '.jpg', '.jpeg')):
        return 'photo'
    elif url.lower().endswith(('.mp4', '.mov')):
        return 'video'
    else:
        return 'unknown'  # or raise an exception


def is_valid_media_type(filename):
    allowed_image_extensions = {'.png', '.jpg', '.jpeg'}
    allowed_video_extensions = {'.mp4', '.mov'}
    extension = os.path.splitext(filename.lower())[1]
    if extension in allowed_image_extensions or extension in allowed_video_extensions:
        return True
    return False
