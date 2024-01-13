from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import BlockedUser
from apps.petprofiles.models import PetProfile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def block_user(request):
    pet_id = request.data.get('pet_id')
    display_pet_profile = get_object_or_404(PetProfile, pet_id=pet_id)

    # Prevent users from blocking themselves
    if request.user == display_pet_profile.user:
        return Response({'error': 'You cannot block your own pet profile'}, status=400)

    # Check if the user has already blocked the target user
    existing_blocked_user = BlockedUser.objects.filter(
        blocker=request.user, blocked=display_pet_profile.user).first()

    if existing_blocked_user:
        # Update the existing instance with the new display_pet_profile
        existing_blocked_user.display_pet_profile = display_pet_profile
        existing_blocked_user.save()
        return Response({'message': 'The display pet profile has been updated for the blocked user.'})
    else:
        # Create a new instance of BlockedUser with the display_pet_profile
        BlockedUser.objects.create(
            blocker=request.user,
            blocked=display_pet_profile.user,
            display_pet_profile=display_pet_profile
        )
        return Response({'message': 'Pet profile and associated user blocked successfully.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unblock_user(request):
    pet_id = request.data.get('pet_id')
    pet_profile = get_object_or_404(PetProfile, pet_id=pet_id)

    blocked_user_relation = BlockedUser.objects.filter(
        blocker=request.user, blocked=pet_profile.user)
    if blocked_user_relation.exists():
        blocked_user_relation.delete()
        return Response({'message': 'Pet profile and associated user unblocked successfully'})
    else:
        return Response({'error': "This pet profile's user is not in your block list"}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_blocked_profiles(request):
    blocked_relations = BlockedUser.objects.filter(
        blocker=request.user).select_related('display_pet_profile')
    blocked_profiles_list = [
        {
            'pet_id': blocked.display_pet_profile.pet_id,
            'pet_name': blocked.display_pet_profile.pet_name,
            'pet_type': blocked.display_pet_profile.pet_type,
            'profile_pic_thumbnail_small': blocked.display_pet_profile.profile_pic_thumbnail_small
        } for blocked in blocked_relations if blocked.display_pet_profile is not None
    ]

    return Response(blocked_profiles_list)
