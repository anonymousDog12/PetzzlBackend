from django.db import models
from django.core.exceptions import ValidationError
from petprofiles.models import PetProfile


class Post(models.Model):
    pet = models.ForeignKey(PetProfile, on_delete=models.CASCADE)
    caption = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Post {self.id} by {self.pet}"


class Media(models.Model):
    # Deleting a post would delete all the media files in that post
    post = models.ForeignKey(Post, related_name='media',
                             on_delete=models.CASCADE)
    media_type = models.CharField(max_length=50, choices=[
                                  ('photo', 'Photo'), ('video', 'Video')])
    media_url = models.URLField(max_length=500)
    thumbnail_medium_url = models.URLField(max_length=500, null=True)
    thumbnail_small_url = models.URLField(max_length=500, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Media {self.id} of Post {self.post.id}"

    def save(self, *args, **kwargs):
        if Media.objects.filter(post=self.post, order=self.order).exclude(id=self.id).exists():
            raise ValidationError(
                f"Media with order {self.order} already exists for this post.")
        super(Media, self).save(*args, **kwargs)
