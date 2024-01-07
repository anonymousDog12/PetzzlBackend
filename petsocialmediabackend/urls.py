from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('api/accounts/', include('accounts.urls')),
    path('api/petprofiles/', include('petprofiles.urls')),
    path('api/mediaposts/', include('mediaposts.urls')),
    path('api/postreactions/', include('postreactions.urls')),
    path('api/userblocking/', include('userblocking.urls')),
]

urlpatterns += [re_path(r'^.*',
                        TemplateView.as_view(template_name='index.html'))]
