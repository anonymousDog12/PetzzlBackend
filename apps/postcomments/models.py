from django.core.validators import MinLengthValidator
from django.db import models

from apps.mediaposts.models import Post
from apps.petprofiles.models import PetProfile


class PostComment(models.Model):
    pet_profile = models.ForeignKey(
        PetProfile, on_delete=models.CASCADE, related_name='comments')  # Author of the comment
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='comments')
    content = models.CharField(
        max_length=500,
        # Ensures content has at least 2 characters
        validators=[MinLengthValidator(2)]
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment by {self.pet_profile.pet_name} on Post {self.post.id}"
