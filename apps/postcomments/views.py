from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated

from apps.mediaposts.models import Post
from apps.petprofiles.models import PetProfile
from apps.userblocking.models import BlockedUser

from .models import PostComment


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, post_id):
    # Parse the request data
    data = JSONParser().parse(request)
    pet_id = data.get('pet_id')

    try:
        post = Post.objects.get(id=post_id)
        pet_profile = PetProfile.objects.get(pet_id=pet_id, user=request.user)
    except (Post.DoesNotExist, PetProfile.DoesNotExist):
        return HttpResponse(status=404)

    post_owner = post.pet.user

    # Check if the user is blocked or has blocked the post owner
    if BlockedUser.objects.filter(blocker=request.user, blocked=post_owner).exists() or \
       BlockedUser.objects.filter(blocker=post_owner, blocked=request.user).exists():
        return JsonResponse({'error': 'Action not allowed'}, status=403)

    content = data.get('content')
    if not content:
        return JsonResponse({'error': 'Content is required'}, status=400)

    comment = PostComment.objects.create(
        pet_profile=pet_profile,
        post=post,
        content=content
    )

    return JsonResponse({'id': comment.id, 'content': comment.content, 'created_at': comment.created_at}, status=201)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    try:
        comment = PostComment.objects.get(id=comment_id)
        post_owner_user = comment.post.pet.user
        comment_owner_user = comment.pet_profile.user
    except PostComment.DoesNotExist:
        return HttpResponse(status=404)

    # Check if the request user is the owner of the pet that authored the comment or the post
    if request.user != post_owner_user and request.user != comment_owner_user:
        return JsonResponse({'error': 'You do not have permission to delete this comment'}, status=403)

    # Delete the comment
    comment.delete()

    return JsonResponse({'message': 'Comment deleted successfully'}, status=204)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_comments_for_post(request, post_id):
    blocked_users = set(BlockedUser.objects.filter(blocker=request.user).values_list('blocked', flat=True)) | \
        set(BlockedUser.objects.filter(
            blocked=request.user).values_list('blocker', flat=True))

    comments = PostComment.objects.filter(post_id=post_id) \
                                  .exclude(pet_profile__user__in=blocked_users) \
                                  .select_related('pet_profile') \
                                  .order_by('-created_at')

    comments_data = [{
        'comment_id': comment.id,
        'pet_id': comment.pet_profile.pet_id,
        'content': comment.content,
        'created_at': comment.created_at.isoformat(),
        'profile_pic_thumbnail_small': comment.pet_profile.profile_pic_thumbnail_small,
        'pet_type': comment.pet_profile.pet_type
    } for comment in comments]

    return JsonResponse({'comments': comments_data}, safe=False, status=200)
