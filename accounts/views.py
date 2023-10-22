from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model

User = get_user_model()


class CheckEmailView(APIView):
    permission_classes = (AllowAny, )

    def post(self, request):
        email = request.data.get('email')

        if User.objects.filter(email=email).exists():
            return Response({"isNewUser": False})
        else:
            return Response({"isNewUser": True})
