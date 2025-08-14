from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add_review/<str:barcode>/', views.add_review, name='add_review'),
    path('favorite/<str:barcode>/', views.add_remove_favorite, name='add_remove_favorite'),
]
