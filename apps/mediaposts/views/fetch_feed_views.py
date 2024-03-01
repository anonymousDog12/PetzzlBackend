from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from apps.contentreporting.models import ReportedContent
from apps.mediaposts.models import Post
from apps.userblocking.models import BlockedUser

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

    # Fetch IDs of posts reported by the current user
    reported_posts_ids = ReportedContent.objects.filter(
        reporter=request.user
    ).values_list('reported_post_id', flat=True)

    # Fetch all posts, excluding those reported by the user and those from blocked users
    all_posts = Post.objects.exclude(
        id__in=reported_posts_ids
    ).exclude(
        pet__user_id__in=all_blocked_users_ids
    ).order_by('-created_at')

    # Apply pagination to the queryset
    paginated_posts = paginator.paginate_queryset(all_posts, request)

    # Convert posts to the response format
    feed = [convert_post_to_response_format(post) for post in paginated_posts]

    return paginator.get_paginated_response(feed)


def convert_post_to_response_format(post):
    media_data = []
    for media in post.media.all():
        media_info = {
            'media_id': media.id,
            'full_size_url': media.media_url,
            'media_type': media.media_type,
        }
        if media.media_type == 'video' and media.thumbnail_small_url:
            media_info['thumbnail_url'] = media.thumbnail_small_url
        media_data.append(media_info)

    pet_profile_pic_url = post.pet.profile_pic_thumbnail_small
    pet_id = post.pet.pet_id
    pet_type = post.pet.pet_type
    created_at_str = post.created_at.strftime('%Y-%m-%d')

    # Fetching the latest comment for the post
    latest_comment = post.comments.order_by('-created_at').first()
    if latest_comment:
        latest_comment_data = {
            'comment_id': latest_comment.id,
            'content': latest_comment.content,
            'pet_id': latest_comment.pet_profile.pet_id,
            'created_at': latest_comment.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        latest_comment_data = None

    # Fetching the total comment count for the post
    comment_count = post.comments.count()

    return {
        'post_id': post.id,
        'caption': post.caption,
        'media': media_data,
        'pet_id': pet_id,
        'pet_profile_pic': pet_profile_pic_url,
        'pet_type': pet_type,
        'posted_date': created_at_str,
        'latest_comment': latest_comment_data,
        'comment_count': comment_count
    }
