from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import BlockedUser
from petprofiles.models import PetProfile


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def block_user(request):
    pet_id = request.data.get('pet_id')
    pet_profile = get_object_or_404(PetProfile, pet_id=pet_id)

    # Prevent users from blocking themselves
    if request.user == pet_profile.user:
        return Response({'error': 'You cannot block your own pet profile'}, status=400)

    # Block the user associated with the pet profile
    # So when one pet profile is blocked, all the other pet profiles
    # owned by the same user will be blocked
    BlockedUser.objects.get_or_create(
        blocker=request.user, blocked=pet_profile.user)
    return Response({'message': 'Pet profile and associated user blocked successfully'})


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
