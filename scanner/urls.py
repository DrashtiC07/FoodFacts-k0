from django.urls import path
from . import views

app_name = 'scanner'

urlpatterns = [
    path('', views.index, name='index'),
    path('scan/', views.scan_barcode, name='scan'),
    path('scan/barcode/', views.scan_barcode, name='scan_barcode'),
    path('scan/manual/', views.manual_entry, name='manual_entry'),
    path('product/<str:barcode>/', views.product_detail, name='product_detail'),
    path('search/', views.search_products, name='search'),
    path('history/', views.scan_history, name='history'),
    path('submit_review/<str:barcode>/', views.submit_review, name='submit_review'),
    path('edit_review/<int:review_id>/', views.edit_review, name='edit_review'),
    path('delete_review/<int:review_id>/', views.delete_review, name='delete_review'),
    path('toggle_favorite/<str:barcode>/', views.toggle_favorite, name='toggle_favorite'),
    path('suggest-nova-group/', views.suggest_nova_group, name='suggest_nova_group'),
]
