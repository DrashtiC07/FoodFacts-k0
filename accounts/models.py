from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from datetime import datetime, timedelta

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
    
    sugar_target = models.IntegerField(default=50, help_text="Daily sugar target in grams")
    sodium_target = models.IntegerField(default=2300, help_text="Daily sodium target in mg")
    fiber_target = models.IntegerField(default=25, help_text="Daily fiber target in grams")
    saturated_fat_target = models.IntegerField(default=20, help_text="Daily saturated fat target in grams")
    
    # Daily consumption tracking
    calories_consumed = models.IntegerField(default=0)
    protein_consumed = models.IntegerField(default=0)
    fat_consumed = models.IntegerField(default=0)
    carbs_consumed = models.IntegerField(default=0)
    
    sugar_consumed = models.IntegerField(default=0)
    sodium_consumed = models.IntegerField(default=0)
    fiber_consumed = models.IntegerField(default=0)
    saturated_fat_consumed = models.IntegerField(default=0)
    
    last_reset_date = models.DateField(default=timezone.now)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def reset_daily_if_needed(self):
        """Reset daily consumption if it's a new day"""
        today = timezone.now().date()
        if self.last_reset_date < today:
            self.calories_consumed = 0
            self.protein_consumed = 0
            self.fat_consumed = 0
            self.carbs_consumed = 0
            self.sugar_consumed = 0
            self.sodium_consumed = 0
            self.fiber_consumed = 0
            self.saturated_fat_consumed = 0
            self.last_reset_date = today
            self.save()

    def get_progress_percentage(self, nutrient):
        """Get progress percentage for a specific nutrient"""
        consumed = getattr(self, f"{nutrient}_consumed", 0)
        target = getattr(self, f"{nutrient}_target", 1)
        return min((consumed / target * 100), 100) if target > 0 else 0

    def __str__(self):
        return f"{self.user.username}'s dietary goals"

class WeeklyNutritionLog(models.Model):
    """Weekly nutrition tracking for trend analysis"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='weekly_logs')
    week_start_date = models.DateField()
    
    # Weekly averages
    avg_calories = models.FloatField(default=0)
    avg_protein = models.FloatField(default=0)
    avg_fat = models.FloatField(default=0)
    avg_carbs = models.FloatField(default=0)
    avg_sugar = models.FloatField(default=0)
    avg_sodium = models.FloatField(default=0)
    avg_fiber = models.FloatField(default=0)
    avg_saturated_fat = models.FloatField(default=0)
    
    # Weekly totals
    total_scans = models.IntegerField(default=0)
    days_tracked = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'week_start_date')
        ordering = ['-week_start_date']

    def __str__(self):
        return f"{self.user.username}'s nutrition log for week of {self.week_start_date}"

class DailyNutritionSnapshot(models.Model):
    """Daily nutrition snapshots for historical tracking"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='daily_snapshots')
    date = models.DateField()
    
    # Daily totals
    calories = models.IntegerField(default=0)
    protein = models.IntegerField(default=0)
    fat = models.IntegerField(default=0)
    carbs = models.IntegerField(default=0)
    sugar = models.IntegerField(default=0)
    sodium = models.IntegerField(default=0)
    fiber = models.IntegerField(default=0)
    saturated_fat = models.IntegerField(default=0)
    
    # Daily targets (for historical comparison)
    calories_target = models.IntegerField(default=2000)
    protein_target = models.IntegerField(default=50)
    fat_target = models.IntegerField(default=70)
    carbs_target = models.IntegerField(default=300)
    sugar_target = models.IntegerField(default=50)
    sodium_target = models.IntegerField(default=2300)
    fiber_target = models.IntegerField(default=25)
    saturated_fat_target = models.IntegerField(default=20)
    
    scans_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def get_goal_achievement_percentage(self):
        """Calculate what percentage of goals were met"""
        goals_met = 0
        total_goals = 8
        
        nutrients = ['calories', 'protein', 'fat', 'carbs', 'sugar', 'sodium', 'fiber', 'saturated_fat']
        for nutrient in nutrients:
            consumed = getattr(self, nutrient, 0)
            target = getattr(self, f"{nutrient}_target", 1)
            
            # For sugar and sodium, being under target is good
            if nutrient in ['sugar', 'sodium', 'saturated_fat']:
                if consumed <= target:
                    goals_met += 1
            else:
                # For other nutrients, being within 80-120% of target is good
                if 0.8 * target <= consumed <= 1.2 * target:
                    goals_met += 1
        
        return (goals_met / total_goals) * 100

    def __str__(self):
        return f"{self.user.username}'s nutrition for {self.date}"
