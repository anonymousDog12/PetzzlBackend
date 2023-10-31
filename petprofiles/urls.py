from django.urls import path
from . import views

urlpatterns = [
    path('pet_profiles/user/<int:user_id>/',
         views.get_pets_by_user, name='get_pets_by_user'),
    path('pet_profiles/', views.pet_profile_list_create,
         name='pet_profile_list_create'),
    path('upload_pet_profile_pic/', views.upload_profile_pic,
         name='upload_profile_pic'),
    path('delete_profile_picture/', views.delete_profile_picture,
         name='delete_profile_picture'),
    path('get_all_pet_ids/', views.get_all_pet_ids, name='get_all_pet_ids'),
    path('check_pet_id_uniqueness/<str:pet_id>/',
         views.check_pet_id_uniqueness, name='check_pet_id_uniqueness'),
]
