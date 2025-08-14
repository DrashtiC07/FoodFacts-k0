from django.contrib import admin
from .models import Product, ScanHistory, NutritionFact, Review

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'barcode', 'health_score', 'nova_group', 'created_at')
    list_filter = ('nova_group', 'vegan', 'vegetarian', 'organic', 'created_at')
    search_fields = ('name', 'brand', 'barcode')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(ScanHistory)
class ScanHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'scanned_at')
    list_filter = ('scanned_at',)
    search_fields = ('user__username', 'product__name')
    ordering = ('-scanned_at',)

@admin.register(NutritionFact)
class NutritionFactAdmin(admin.ModelAdmin):
    list_display = ('product', 'energy_kcal', 'proteins', 'fat', 'carbohydrates')
    search_fields = ('product__name',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__name')
    ordering = ('-created_at',)
