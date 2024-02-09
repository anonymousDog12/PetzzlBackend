import os
from urllib.parse import urlparse

import boto3
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.mediaposts.models import Post


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_post(request, post_id):
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
