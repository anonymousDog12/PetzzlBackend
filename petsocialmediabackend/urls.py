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
    path('api/petprofiles/', include('apps.petprofiles.urls')),
    path('api/mediaposts/', include('apps.mediaposts.urls')),
    path('api/postreactions/', include('apps.postreactions.urls')),
    path('api/userblocking/', include('apps.userblocking.urls')),
    path('api/contentreporting/', include('apps.contentreporting.urls')),
]

urlpatterns += [re_path(r'^.*',
                        TemplateView.as_view(template_name='index.html'))]
