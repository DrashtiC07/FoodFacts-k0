from django.db import models
from django.core.validators import MinLengthValidator
from django.contrib.auth import get_user_model

User = get_user_model() # Get the CustomUser model


class Product(models.Model):
    ALLERGENS = [
        ('peanuts', 'Peanuts'),
        ('tree_nuts', 'Tree Nuts'),
        ('milk', 'Milk'),
        ('eggs', 'Eggs'),
        ('fish', 'Fish'),
        ('shellfish', 'Shellfish'),
        ('soy', 'Soy'),
        ('wheat', 'Wheat'),
        ('gluten', 'Gluten'),
        ('sesame', 'Sesame'),
    ]
    
    barcode = models.CharField(
        max_length=20, 
        unique=True,
        validators=[MinLengthValidator(8)]
    )
    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=255, blank=True)
    ingredients = models.TextField(blank=True)
    nutrition_info = models.JSONField(default=dict, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    ecoscore = models.CharField(max_length=1, blank=True)
    nova_group = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    vegan = models.BooleanField(null=True, blank=True)  # Allows NULL in database
    vegetarian = models.BooleanField(null=True, blank=True)  # Apply same to vegetarian
    palm_oil_free = models.BooleanField(null=True, blank=True)  # And palm_oil_free
    organic = models.BooleanField(null=True, blank=True)  # And organic
    allergens = models.JSONField(default=list, blank=True) 
    health_score = models.PositiveSmallIntegerField(null=True, blank=True)
    
    def get_nova_description(self):
        nova_descriptions = {
            1: "Unprocessed or minimally processed foods",
            2: "Processed culinary ingredients",
            3: "Processed foods",
            4: "Ultra-processed foods"
        }
        return nova_descriptions.get(self.nova_group, "Not specified")

    def detect_allergens(self, ingredients=None):
        ingredients_to_check = ingredients if ingredients is not None else self.ingredients
        
        if not ingredients_to_check:
            return []
        
        detected = []
        ingredients_lower = ingredients_to_check.lower()
        
        for allergen_id, allergen_name in self.ALLERGENS:
            keywords = {
                'peanuts': ['peanut', 'arachis oil'],
                'tree_nuts': ['almond', 'walnut', 'cashew', 'pistachio', 'hazelnut', 'pecan', 'macadamia'],
                'milk': ['milk', 'whey', 'casein', 'lactose', 'butter', 'cream', 'cheese'],
                'eggs': ['egg', 'albumin', 'ovalbumin'],
                'fish': ['fish', 'tuna', 'salmon', 'anchovy'],
                'shellfish': ['shrimp', 'prawn', 'crab', 'lobster', 'shellfish'],
                'soy': ['soy', 'soya', 'tofu', 'edamame'],
                'wheat': ['wheat', 'bulgur', 'farina'],
                'gluten': ['gluten', 'wheat', 'barley', 'rye', 'malt'],
                'sesame': ['sesame', 'tahini'],
            }.get(allergen_id, [])
            
            if any(keyword in ingredients_lower for keyword in keywords):
                detected.append(allergen_id)
                
        return detected

    def calculate_health_score(self):
        if not self.nutrition_info:
            return None

        # Base score (50 is neutral)
        score = 50
    
    # Nutrient scoring parameters (points per gram)
        nutrient_scores = {
            # Negative impact nutrients (subtract points)
            'saturated-fat': -5,
            'trans-fat': -20,      # Very bad
            'sugars': -3,
            'added-sugars': -4,    # Worse than natural sugars
            'salt': -20,           # Points per gram (salt is in small amounts)
            'sodium': -15,         # Alternative to salt
            'cholesterol': -0.5,   # Points per mg
            
            # Positive impact nutrients (add points)
            'fiber': 10,
            'proteins': 2,
            'unsaturated-fat': 1,  # Healthy fats
            'polyunsaturated-fat': 2,
            'monounsaturated-fat': 2,
            'omega-3': 3,          # Healthy fatty acids
            'vitamin-a': 0.1,      # Points per % of DV
            'vitamin-c': 0.1,
            'vitamin-d': 0.1,
            'vitamin-e': 0.1,
            'vitamin-k': 0.1,
            'calcium': 0.1,
            'iron': 0.1,
            'potassium': 0.05,
            'magnesium': 0.1,
        }
        
        # Calculate score based on nutrients
        for nutrient, value in self.nutrition_info.items():
            if isinstance(value, (int, float)):
                # Normalize keys (handle different naming conventions)
                norm_nutrient = nutrient.lower().replace('_', '-').replace(' ', '-')
                
                # Get the score multiplier for this nutrient
                multiplier = nutrient_scores.get(norm_nutrient, 0)
                
                # Apply multiplier to value
                score += value * multiplier
        
        # Apply additional scoring factors
        additional_factors = {
            # Processing level (NOVA groups)
            'nova_group': {
                1: 10,   # Unprocessed - bonus
                2: 5,     # Minimally processed - small bonus
                3: -5,    # Processed - penalty
                4: -15    # Ultra-processed - big penalty
            },
            
            # Organic status
            'organic': {
                True: 5,   # Bonus for organic
                False: 0
            },
            
            # Allergens (more allergens = worse)
            'allergens_count': lambda x: -2 * len(x) if x else 0
        }
        
        # Apply NOVA group factor if available
        if self.nova_group:
            score += additional_factors['nova_group'].get(self.nova_group, 0)
        
        # Apply organic factor
        score += additional_factors['organic'].get(self.organic, 0)
        
        # Apply allergens factor
        if hasattr(self, 'allergens'):
            score += additional_factors['allergens_count'](self.allergens)
        
        # Apply vegan/vegetarian bonuses
        if self.vegan:
            score += 3
        elif self.vegetarian:
            score += 1
        
        # Apply palm oil penalty
        if not self.palm_oil_free:
            score -= 5
        
        # Ensure score is within bounds (0-100)
        score = max(0, min(100, int(score)))
        
        # Round to nearest 5 for cleaner presentation
        return ((score + 2) // 5) * 5

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return sum(review.rating for review in reviews) / len(reviews)
        return 0

    @property
    def review_count(self):
        return self.reviews.count()

    def __str__(self):
        return f"{self.name} ({self.barcode})"
        
        
        
class ScanHistory(models.Model):
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']
        verbose_name_plural = "Scan History"

    def __str__(self):
        return f"{self.user.username} scanned {self.product.name} at {self.scanned_at.strftime('%Y-%m-%d %H:%M')}"


class NutritionFact(models.Model):
    """Detailed nutrition facts for products"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='nutrition_facts')
    energy_kcal = models.FloatField(null=True, blank=True)
    fat = models.FloatField(null=True, blank=True)
    saturated_fat = models.FloatField(null=True, blank=True)
    carbohydrates = models.FloatField(null=True, blank=True)
    sugars = models.FloatField(null=True, blank=True)
    proteins = models.FloatField(null=True, blank=True)
    salt = models.FloatField(null=True, blank=True)
    fiber = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Nutrition facts for {self.product.name}"


class Review(models.Model):
    """Product reviews"""
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='product_reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_reviews')
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s review of {self.product.name}"
