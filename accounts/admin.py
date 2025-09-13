from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ProductReview, FavoriteProduct, DietaryGoal


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = ("username", "email", "first_name", "last_name", "is_staff")

    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("phone_number", "date_of_birth","profile_picture")}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("phone_number", "date_of_birth", "profile_picture")}),
    )

admin.site.register(CustomUser, CustomUserAdmin)


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
