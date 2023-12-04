from django.db import models
from mediaposts.models import Post
from petprofiles.models import PetProfile


class PostReaction(models.Model):
    # Reference to PetProfile instead of User
    pet_profile = models.ForeignKey(PetProfile, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=50, default='like')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Prevents multiple reactions by the same pet on the same post
        unique_together = ('pet_profile', 'post')

    def __str__(self):
        return f"{self.reaction_type.title()} {self.id} on Post {self.post.id} by {self.pet_profile.pet_name}"
