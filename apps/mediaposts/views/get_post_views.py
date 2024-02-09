from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.contentreporting.models import ReportedContent
from apps.mediaposts.models import PetProfile, Post
from apps.userblocking.models import BlockedUser


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_post_media(request, post_id, detail_level='overview'):
    post = get_object_or_404(Post, pk=post_id)
    user = request.user

    # Check if the post has been reported by the current user or if there's a block
    if ReportedContent.objects.filter(reporter=user, reported_post=post).exists() or \
       post.pet.user.id in set(BlockedUser.objects.filter(blocker=user).values_list('blocked', flat=True)) or \
       post.pet.user.id in set(BlockedUser.objects.filter(blocked=user).values_list('blocker', flat=True)):
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

    # Fetch IDs of posts reported by the current user
    reported_posts_ids = ReportedContent.objects.filter(
        reporter=user
    ).values_list('reported_post_id', flat=True)

    # Fetch sets of users who have been blocked or have blocked the current user
    blocked_users = set(BlockedUser.objects.filter(
        blocker=user).values_list('blocked', flat=True))
    users_blocking = set(BlockedUser.objects.filter(
        blocked=user).values_list('blocker', flat=True))

    # Combine the sets to check if there is a block in either direction
    if pet.user.id in blocked_users or pet.user.id in users_blocking:
        # No posts should be shown if the user is blocked or is blocking
        return Response([])

    # Fetch all posts for a given pet profile, excluding reported and posts from blocked users
    pet_posts = Post.objects.filter(
        pet_id=pet_id
    ).exclude(
        id__in=reported_posts_ids
    ).order_by('-created_at')

    response_data = []
    for post in pet_posts:
        media_count = post.media.count()
        first_media = post.media.first()  # Get the first media item
        if first_media:
            post_data = {
                'post_id': post.id,
                'caption': post.caption,
                'thumbnail_url': first_media.thumbnail_small_url,
                'has_multiple_images': media_count > 1
                # Add any other necessary post details
            }
            response_data.append(post_data)

    return Response(response_data)
