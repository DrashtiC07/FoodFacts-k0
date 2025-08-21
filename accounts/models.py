from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date, timedelta
from django.utils import timezone

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

class TrackedItem(models.Model):
    """Items added to user's nutrition tracker"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tracked_items')
    product = models.ForeignKey('scanner.Product', on_delete=models.CASCADE, related_name='tracked_by')
    serving_size = models.FloatField(default=100.0, help_text="Serving size in grams")
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-added_at']
    
    @property
    def calculated_nutrition(self):
        """Calculate nutrition values based on serving size"""
        if not self.product.nutrition_info:
            return None
        
        multiplier = self.serving_size / 100  # Nutrition info is per 100g
        nutrition = {}
        
        for key, value in self.product.nutrition_info.items():
            if isinstance(value, (int, float)):
                nutrition[key] = value * multiplier
        
        return nutrition
    
    def __str__(self):
        return f"{self.user.username} tracked {self.product.name} ({self.serving_size}g)"

class DietaryGoal(models.Model):
    """User's dietary goals and tracking"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='dietary_goals')
    calories_target = models.IntegerField(default=2000)
    protein_target = models.IntegerField(default=50)
    fat_target = models.IntegerField(default=70)
    carbs_target = models.IntegerField(default=300)
    
    sugar_target = models.IntegerField(default=50)  # grams per day
    sodium_target = models.IntegerField(default=2300)  # mg per day
    fiber_target = models.IntegerField(default=25)  # grams per day
    
    calories_consumed = models.IntegerField(default=0)
    protein_consumed = models.IntegerField(default=0)
    fat_consumed = models.IntegerField(default=0)
    carbs_consumed = models.IntegerField(default=0)
    sugar_consumed = models.IntegerField(default=0)
    sodium_consumed = models.IntegerField(default=0)
    fiber_consumed = models.IntegerField(default=0)
    
    last_reset_date = models.DateField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def reset_daily_if_needed(self):
        """Reset daily consumption if it's a new day"""
        today = date.today()
        if self.last_reset_date < today:
            self.calories_consumed = 0
            self.protein_consumed = 0
            self.fat_consumed = 0
            self.carbs_consumed = 0
            self.sugar_consumed = 0
            self.sodium_consumed = 0
            self.fiber_consumed = 0
            self.last_reset_date = today
            self.save()

    def get_progress_percentage(self, nutrient):
        """Calculate progress percentage for a specific nutrient"""
        consumed = getattr(self, f'{nutrient}_consumed', 0)
        target = getattr(self, f'{nutrient}_target', 1)
        return min(100, (consumed / target) * 100) if target > 0 else 0

    def add_nutrition(self, calories=0, protein=0, fat=0, carbs=0, sugar=0, sodium=0, fiber=0):
        """Add nutrition values to daily consumption"""
        self.reset_daily_if_needed()
        self.calories_consumed += calories
        self.protein_consumed += protein
        self.fat_consumed += fat
        self.carbs_consumed += carbs
        self.sugar_consumed += sugar
        self.sodium_consumed += sodium
        self.fiber_consumed += fiber
        self.save()

    def __str__(self):
        return f"{self.user.username}'s dietary goals"

class WeeklyNutritionLog(models.Model):
    """Weekly nutrition tracking for trend analysis"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='weekly_logs')
    week_start_date = models.DateField()
    
    avg_calories = models.FloatField(default=0)
    avg_protein = models.FloatField(default=0)
    avg_fat = models.FloatField(default=0)
    avg_carbs = models.FloatField(default=0)
    avg_sugar = models.FloatField(default=0)
    avg_sodium = models.FloatField(default=0)
    avg_fiber = models.FloatField(default=0)
    
    calories_achievement = models.FloatField(default=0)
    protein_achievement = models.FloatField(default=0)
    fat_achievement = models.FloatField(default=0)
    carbs_achievement = models.FloatField(default=0)
    sugar_achievement = models.FloatField(default=0)
    sodium_achievement = models.FloatField(default=0)
    fiber_achievement = models.FloatField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'week_start_date')
        ordering = ['-week_start_date']

    def __str__(self):
        return f"{self.user.username}'s nutrition log for week of {self.week_start_date}"

class DailyNutritionSnapshot(models.Model):
    """Daily nutrition snapshot for historical tracking"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='daily_snapshots')
    date = models.DateField()
    
    calories = models.IntegerField(default=0)
    protein = models.IntegerField(default=0)
    fat = models.IntegerField(default=0)
    carbs = models.IntegerField(default=0)
    sugar = models.IntegerField(default=0)
    sodium = models.IntegerField(default=0)
    fiber = models.IntegerField(default=0)
    
    goals_met = models.IntegerField(default=0)  # Number of goals achieved
    total_goals = models.IntegerField(default=7)  # Total number of tracked nutrients
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username}'s nutrition for {self.date}"

class PersonalizedTip(models.Model):
    """Persistent personalized tips that remain visible until updated"""
    TIP_TYPES = [
        ('critical', 'Critical Alert'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('info', 'Information'),
    ]
    
    PRIORITY_LEVELS = [
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Medium'),
        (4, 'Low'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='personalized_tips')
    tip_type = models.CharField(max_length=20, choices=TIP_TYPES, default='info')
    priority = models.IntegerField(choices=PRIORITY_LEVELS, default=3)
    icon = models.CharField(max_length=50, default='info-circle')
    color = models.CharField(max_length=20, default='info')
    title = models.CharField(max_length=100)
    message = models.TextField()
    
    # Tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_nutrition_snapshot = models.JSONField(default=dict, blank=True)  # Store nutrition data when tip was created
    is_active = models.BooleanField(default=True)
    
    # Conditions for tip relevance
    trigger_condition = models.CharField(max_length=100, blank=True)  # e.g., 'sugar_progress > 90'
    
    class Meta:
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.get_tip_type_display()})"
    
    def is_still_relevant(self, current_nutrition_data):
        """Check if tip is still relevant based on current nutrition data"""
        if not self.trigger_condition:
            return True
            
        # Parse trigger condition and evaluate against current data
        try:
            # Simple evaluation for common conditions
            if 'sugar_progress > 90' in self.trigger_condition:
                return current_nutrition_data.get('sugar_progress', 0) > 90
            elif 'sodium_progress > 90' in self.trigger_condition:
                return current_nutrition_data.get('sodium_progress', 0) > 90
            elif 'protein_progress < 50' in self.trigger_condition:
                return current_nutrition_data.get('protein_progress', 0) < 50
            elif 'calories_progress < 40' in self.trigger_condition:
                return current_nutrition_data.get('calories_progress', 0) < 40
            elif 'fat_progress > 85' in self.trigger_condition:
                return current_nutrition_data.get('fat_progress', 0) > 85
            # Add more conditions as needed
            return True
        except:
            return True
