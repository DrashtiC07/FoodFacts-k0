from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class CustomUser(AbstractUser):
    """Extended user model with additional fields"""
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    def __str__(self):
        return self.username

class ProductReview(models.Model):
    """Product review model"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey('scanner.Product', on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    review_text = models.TextField(blank=True, null=True, help_text="Optional review text")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s review of {self.product.name} - {self.rating} stars"

class FavoriteProduct(models.Model):
    """User's favorite products"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='favorite_products')
    product = models.ForeignKey('scanner.Product', on_delete=models.CASCADE, related_name='favorited_by')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username}'s favorite: {self.product.name}"

class DietaryGoal(models.Model):
    """User's dietary goals and tracking"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='dietary_goals')
    calories_target = models.IntegerField(default=2000)
    protein_target = models.IntegerField(default=50)
    fat_target = models.IntegerField(default=70)
    carbs_target = models.IntegerField(default=300)
    
    # Daily consumption tracking
    calories_consumed = models.IntegerField(default=0)
    protein_consumed = models.IntegerField(default=0)
    fat_consumed = models.IntegerField(default=0)
    carbs_consumed = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s dietary goals"
