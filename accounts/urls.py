from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('add_review/<str:barcode>/', views.add_review, name='add_review'),
    path('favorite/<str:barcode>/', views.add_remove_favorite, name='add_remove_favorite'),
    path('update_nutrition_goals/', views.update_nutrition_goals, name='update_nutrition_goals'),
    path('reset_daily_goals/', views.reset_daily_goals, name='reset_daily_goals'),
    path('add_to_nutrition_tracker/', views.add_to_nutrition_tracker, name='add_to_nutrition_tracker'),
]
