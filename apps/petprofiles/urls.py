from django.urls import path
from . import views

urlpatterns = [
    path('pet_profiles/user/<int:user_id>/',
         views.get_pets_by_user, name='get_pets_by_user'),
    path('pet_profiles/', views.pet_profile_list_create,
         name='pet_profile_list_create'),
    path('pet_profiles/<str:pet_id>/delete/',
         views.delete_pet_profile, name='delete_pet_profile'),
    path('upload_pet_profile_pic/', views.upload_profile_pic,
         name='upload_profile_pic'),
    path('delete_profile_picture/', views.delete_profile_picture,
         name='delete_profile_picture'),
    path('check_pet_id_uniqueness/<str:pet_id>/',
         views.check_pet_id_uniqueness, name='check_pet_id_uniqueness'),
    path('pet_profiles/<str:pet_id>/',
         views.pet_profile_detail, name='pet_profile_detail'),
]
