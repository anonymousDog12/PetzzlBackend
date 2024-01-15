from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Post, ReportedContent


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_post(request):
    post_id = request.data.get('post_id')
    reason = request.data.get('reason')
    details = request.data.get('details', '')

    post = get_object_or_404(Post, id=post_id)

    # Check if the user is trying to report their own post
    if request.user == post.pet.user:
        return Response({'error': 'You cannot report your own content.'}, status=400)

     # Check if the post has already been reported by this user
    if ReportedContent.objects.filter(reported_post=post, reporter=request.user).exists():
        return Response({'message': "Thank you for your vigilance! You've already reported this post, and we're looking into it."})

    # Create report
    report = ReportedContent.objects.create(
        reporter=request.user,
        reported_post=post,
        reason=reason,
        details=details
    )

    # Send email notification
    subject = f'New Report for Post ID {post_id}'
    message = (f'A new report has been filed.\n\n'
               f'Report ID: {report.id}\n'
               f'Reporter: {request.user.email}\n'
               f'Post ID: {post_id}\n'
               f'Reason: {report.get_reason_display()}\n'
               f'Details: {details}')
    # Add additional email here
    recipient_list = ['admin@petzzl.app']
    send_mail(subject, message, 'admin@petzzl.app', recipient_list)

    return Response({'message': 'Your report has been submitted. Thank you for helping us keep our community safe.'})
