from rest_framework import serializers
from .models import PetProfile


class PetProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PetProfile
        fields = ('pet_id', 'user', 'pet_name', 'pet_type', 'birthday',
                  'profile_pic_regular',
                  'profile_pic_thumbnail_small',
                  'gender',
                  'bio',
                  'created_at',
                  'updated_at')
        read_only_fields = ('user', 'created_at', 'updated_at')
