from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BlockedUser(models.Model):
    blocker = models.ForeignKey(
        User, related_name='blocker', on_delete=models.CASCADE)
    blocked = models.ForeignKey(
        User, related_name='blocked', on_delete=models.CASCADE)
    blocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"

    def clean(self):
        if self.blocker == self.blocked:
            raise ValidationError("Cannot block oneself.")

    def save(self, *args, **kwargs):
        self.clean()
        super(BlockedUser, self).save(*args, **kwargs)
