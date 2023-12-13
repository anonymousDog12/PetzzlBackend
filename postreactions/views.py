from .models import Post, PostReaction
from rest_framework.permissions import AllowAny
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


@api_view(['GET'])
@permission_classes([AllowAny])
def get_like_count(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
        like_count = PostReaction.objects.filter(
            post=post, reaction_type='like').count()
        return Response({'like_count': like_count}, status=status.HTTP_200_OK)
    except Post.DoesNotExist:
        return Response({'message': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_like_status(request, post_id, pet_profile_id):
    try:
        post = Post.objects.get(pk=post_id)
        pet_profile = PetProfile.objects.get(
            pk=pet_profile_id, user=request.user)
    except (Post.DoesNotExist, PetProfile.DoesNotExist):
        # If either post or pet profile does not exist, return liked as False
        return Response({'liked': False}, status=status.HTTP_200_OK)

    liked = PostReaction.objects.filter(
        pet_profile=pet_profile, post=post, reaction_type='like').exists()
    return Response({'liked': liked}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_likers_of_post(request, post_id):
    try:
        post = Post.objects.get(pk=post_id)
        reactions = PostReaction.objects.filter(
            post=post, reaction_type='like').select_related('pet_profile')
        likers = reactions.values(
            'pet_profile__pet_id',
            'pet_profile__profile_pic_thumbnail_small',
            'pet_profile__pet_type'
        )
        return Response({'likers': list(likers)}, status=status.HTTP_200_OK)
    except Post.DoesNotExist:
        return Response({'message': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
