from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ProductReview, FavoriteProduct, DietaryGoal

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone_number', 'date_of_birth', 'profile_picture')}),
    )

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'product__name')
    ordering = ('-created_at',)

@admin.register(FavoriteProduct)
class FavoriteProductAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'product__name')
    ordering = ('-added_at',)

@admin.register(DietaryGoal)
class DietaryGoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'calories_target', 'protein_target', 'fat_target', 'carbs_target')
    search_fields = ('user__username',)
