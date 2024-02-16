from django.db import models
from django.contrib.auth import get_user_model
from apps.mediaposts.models import Post
from django.core.exceptions import ValidationError

User = get_user_model()


class ReportReason(models.TextChoices):
    I_JUST_DONT_LIKE_IT = 'DL', 'I Just Don\'t Like It'
    NOT_A_PET_PHOTO = 'NP', 'Not a Pet Photo'
    SELF_PROMOTION = 'SP', 'Self Promotion'
    INAPPROPRIATE_CONTENT = 'IC', 'Inappropriate Content'
    COPYRIGHT_ISSUE = 'IP', 'Intellectual Property Violation'
    VIOLENCE_OR_DANGEROUS_ORGANIZATIONS = 'VD', 'Violence or Dangerous Organizations'
    NUDITY_OR_SEXUAL_ACTIVITY = 'NS', 'Nudity or Sexual Activity'
    OTHER = 'OT', 'Other'


class ReportedContent(models.Model):
    reporter = models.ForeignKey(
        User, related_name='reporter_relations', on_delete=models.CASCADE)
    reported_post = models.ForeignKey(
        Post, related_name='reported_posts', on_delete=models.CASCADE)
    reason = models.CharField(
        max_length=2,
        choices=ReportReason.choices,
        default=ReportReason.OTHER
    )
    # Limited to 500 characters
    details = models.CharField(max_length=500, blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    is_reviewed = models.BooleanField(default=False)

    # TODO: enforce action_taken field only editable by admins
    action_taken = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = ('reporter', 'reported_post')

    def __str__(self):
        return f"{self.reporter.username} reported Post {self.reported_post.id} for {self.get_reason_display()}"

    def clean(self):
        if self.reporter == self.reported_post.pet.user:
            raise ValidationError("Cannot report one's own post.")
