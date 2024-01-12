from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from petprofiles.models import PetProfile

User = get_user_model()


class BlockedUser(models.Model):
    blocker = models.ForeignKey(
        User, related_name='blocker_relations', on_delete=models.CASCADE)
    blocked = models.ForeignKey(
        User, related_name='blocked_relations', on_delete=models.CASCADE)
    display_pet_profile = models.ForeignKey(
        PetProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_display_profile',
        help_text='The pet profile that was displayed to the blocker when the block was made.'
    )
    blocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        if self.display_pet_profile:
            return f"{self.blocker.username} blocked {self.blocked.username} displaying {self.display_pet_profile.pet_id}"
        else:
            return f"{self.blocker.username} blocked {self.blocked.username} but display profile is no longer available"

    def clean(self):
        if self.blocker == self.blocked:
            raise ValidationError("Cannot block oneself.")
        if self.display_pet_profile and self.display_pet_profile.user != self.blocked:
            raise ValidationError(
                "The display pet profile must belong to the blocked user.")
