from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import PostReaction
from mediaposts.models import Post
from petprofiles.models import PetProfile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def like_post(request, post_id, pet_profile_id):
    try:
        post = Post.objects.get(pk=post_id)
        pet_profile = PetProfile.objects.get(
            pk=pet_profile_id, user=request.user)
        reaction, created = PostReaction.objects.get_or_create(
            pet_profile=pet_profile,
            post=post,
            defaults={'reaction_type': 'like'}
        )
        if not created:
            return Response({'message': 'Already liked'}, status=status.HTTP_409_CONFLICT)
        return Response({'message': 'Liked'}, status=status.HTTP_201_CREATED)
    except (Post.DoesNotExist, PetProfile.DoesNotExist):
        return Response({'message': 'Post or Pet Profile not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unlike_post(request, post_id, pet_profile_id):
    try:
        post = Post.objects.get(pk=post_id)
        pet_profile = PetProfile.objects.get(
            pk=pet_profile_id, user=request.user)
        try:
            reaction = PostReaction.objects.get(
                pet_profile=pet_profile, post=post)
            reaction.delete()
            return Response({'message': 'Unliked'}, status=status.HTTP_200_OK)
        except PostReaction.DoesNotExist:
            return Response({'message': 'Not liked yet'}, status=status.HTTP_404_NOT_FOUND)
    except (Post.DoesNotExist, PetProfile.DoesNotExist):
        return Response({'message': 'Post or Pet Profile not found'}, status=status.HTTP_404_NOT_FOUND)
