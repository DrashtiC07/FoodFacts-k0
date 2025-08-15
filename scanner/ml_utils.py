"""
Machine Learning utilities for eco-score prediction and food analysis
"""
import logging
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)

class EcoScorePredictor:
    """
    Simple ML-based eco-score predictor using rule-based classification
    with nutritional and ingredient analysis
    """
    
    def __init__(self):
        # Eco-friendly ingredient keywords (positive impact)
        self.eco_positive_keywords = [
            'organic', 'bio', 'natural', 'sustainable', 'fair trade',
            'locally sourced', 'free range', 'grass fed', 'wild caught',
            'renewable', 'recyclable', 'biodegradable', 'plant based',
            'vegan', 'vegetarian', 'non-gmo', 'pesticide free'
        ]
        
        # Eco-unfriendly keywords (negative impact)
        self.eco_negative_keywords = [
            'palm oil', 'artificial', 'synthetic', 'preservative',
            'colorant', 'flavor enhancer', 'stabilizer', 'emulsifier',
            'high fructose corn syrup', 'trans fat', 'hydrogenated',
            'monosodium glutamate', 'msg', 'nitrate', 'nitrite'
        ]
        
        # Processing level indicators
        self.processing_indicators = {
            'minimal': ['fresh', 'raw', 'whole', 'unprocessed', 'natural'],
            'moderate': ['cooked', 'dried', 'frozen', 'canned', 'pasteurized'],
            'high': ['refined', 'processed', 'enriched', 'fortified', 'modified'],
            'ultra': ['artificial', 'synthetic', 'reconstituted', 'hydrolyzed', 'isolated']
        }
    
    def predict_ecoscore(self, product_data: Dict[str, Any]) -> str:
        """
        Predict eco-score based on available product data
        Returns: A, B, C, D, or E (A being best, E being worst)
        """
        try:
            score = 50  # Start with neutral score
            
            # Analyze ingredients (40% weight)
            ingredients_score = self._analyze_ingredients(product_data.get('ingredients', ''))
            score += ingredients_score * 0.4
            
            # Analyze nutrition (30% weight)
            nutrition_score = self._analyze_nutrition(product_data.get('nutrition_info', {}))
            score += nutrition_score * 0.3
            
            # Analyze processing level (20% weight)
            processing_score = self._analyze_processing_level(
                product_data.get('nova_group'),
                product_data.get('ingredients', '')
            )
            score += processing_score * 0.2
            
            # Analyze category (10% weight)
            category_score = self._analyze_category(product_data.get('category', ''))
            score += category_score * 0.1
            
            # Convert score to letter grade
            return self._score_to_grade(score)
            
        except Exception as e:
            logger.error(f"Error predicting eco-score: {e}")
            return 'C'  # Default to neutral score
    
    def _analyze_ingredients(self, ingredients: str) -> float:
        """Analyze ingredients for eco-friendliness"""
        if not ingredients:
            return 0
        
        ingredients_lower = ingredients.lower()
        score = 0
        
        # Check for eco-positive ingredients
        positive_count = sum(1 for keyword in self.eco_positive_keywords 
                           if keyword in ingredients_lower)
        score += positive_count * 10
        
        # Check for eco-negative ingredients
        negative_count = sum(1 for keyword in self.eco_negative_keywords 
                           if keyword in ingredients_lower)
        score -= negative_count * 15
        
        # Bonus for shorter ingredient lists (less processed)
        ingredient_count = len([i.strip() for i in ingredients.split(',') if i.strip()])
        if ingredient_count <= 5:
            score += 10
        elif ingredient_count <= 10:
            score += 5
        elif ingredient_count > 20:
            score -= 10
        
        return max(-50, min(50, score))
    
    def _analyze_nutrition(self, nutrition: Dict[str, Any]) -> float:
        """Analyze nutritional content for eco-impact"""
        if not nutrition:
            return 0
        
        score = 0
        
        # High sugar content (often indicates processing)
        sugars = nutrition.get('sugars_100g', nutrition.get('sugars', 0))
        if isinstance(sugars, (int, float)):
            if sugars > 20:
                score -= 15
            elif sugars > 10:
                score -= 8
        
        # High sodium content (processing indicator)
        sodium = nutrition.get('sodium_100g', nutrition.get('salt_100g', 0))
        if isinstance(sodium, (int, float)):
            if sodium > 1.5:  # High sodium
                score -= 12
            elif sodium > 0.8:
                score -= 6
        
        # High saturated fat (often from animal products)
        sat_fat = nutrition.get('saturated-fat_100g', nutrition.get('saturated_fat', 0))
        if isinstance(sat_fat, (int, float)):
            if sat_fat > 10:
                score -= 10
            elif sat_fat > 5:
                score -= 5
        
        # High fiber content (good for environment, less processed)
        fiber = nutrition.get('fiber_100g', nutrition.get('fiber', 0))
        if isinstance(fiber, (int, float)):
            if fiber > 10:
                score += 15
            elif fiber > 5:
                score += 8
        
        return max(-30, min(30, score))
    
    def _analyze_processing_level(self, nova_group: Optional[int], ingredients: str) -> float:
        """Analyze processing level impact"""
        score = 0
        
        # NOVA group analysis
        if nova_group:
            nova_scores = {1: 20, 2: 10, 3: -10, 4: -25}
            score += nova_scores.get(nova_group, 0)
        
        # Ingredient-based processing analysis
        if ingredients:
            ingredients_lower = ingredients.lower()
            
            for level, keywords in self.processing_indicators.items():
                count = sum(1 for keyword in keywords if keyword in ingredients_lower)
                
                if level == 'minimal':
                    score += count * 5
                elif level == 'moderate':
                    score += count * 2
                elif level == 'high':
                    score -= count * 3
                elif level == 'ultra':
                    score -= count * 8
        
        return max(-40, min(40, score))
    
    def _analyze_category(self, category: str) -> float:
        """Analyze product category for environmental impact"""
        if not category:
            return 0
        
        category_lower = category.lower()
        
        # Eco-friendly categories
        eco_friendly = [
            'fruits', 'vegetables', 'legumes', 'grains', 'cereals',
            'plant-based', 'organic', 'natural', 'herbal'
        ]
        
        # Less eco-friendly categories
        less_eco_friendly = [
            'meat', 'beef', 'pork', 'processed meat', 'fast food',
            'snacks', 'candy', 'soft drinks', 'energy drinks'
        ]
        
        for friendly in eco_friendly:
            if friendly in category_lower:
                return 10
        
        for unfriendly in less_eco_friendly:
            if unfriendly in category_lower:
                return -15
        
        return 0
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numerical score to letter grade"""
        if score >= 70:
            return 'A'
        elif score >= 50:
            return 'B'
        elif score >= 30:
            return 'C'
        elif score >= 10:
            return 'D'
        else:
            return 'E'

class NovaGroupAnalyzer:
    """
    Analyzer for NOVA food classification system
    """
    
    @staticmethod
    def get_nova_info(nova_group: Optional[int]) -> Dict[str, Any]:
        """Get comprehensive information about NOVA group"""
        nova_data = {
            1: {
                'name': 'Unprocessed or minimally processed foods',
                'description': 'Natural foods obtained directly from plants or animals and do not undergo any alteration following their removal from nature.',
                'examples': [
                    'Fresh fruits and vegetables',
                    'Grains, legumes, nuts, seeds',
                    'Fresh meat, poultry, fish',
                    'Eggs, milk',
                    'Natural yogurt (no added sugar)',
                    'Herbs, spices, tea, coffee'
                ],
                'health_impact': 'Excellent - These foods form the basis of a healthy diet',
                'environmental_impact': 'Generally low environmental impact',
                'color': 'success',
                'icon': 'leaf',
                'recommendation': 'Make these foods the foundation of your diet'
            },
            2: {
                'name': 'Processed culinary ingredients',
                'description': 'Substances derived from Group 1 foods or from nature by processes such as pressing, refining, grinding, milling, and drying.',
                'examples': [
                    'Oils, butter, lard',
                    'Sugar, salt',
                    'Flour, pasta',
                    'Vinegar',
                    'Honey, maple syrup'
                ],
                'health_impact': 'Good - Use in small amounts to prepare Group 1 foods',
                'environmental_impact': 'Low to moderate environmental impact',
                'color': 'info',
                'icon': 'droplet',
                'recommendation': 'Use in moderation to enhance Group 1 foods'
            },
            3: {
                'name': 'Processed foods',
                'description': 'Products made by adding salt, oil, sugar or other Group 2 substances to Group 1 foods.',
                'examples': [
                    'Canned vegetables with added salt',
                    'Canned fish in oil',
                    'Fruits in syrup',
                    'Cheese, bread',
                    'Salted nuts',
                    'Smoked meats'
                ],
                'health_impact': 'Fair - Consume in moderation as part of balanced meals',
                'environmental_impact': 'Moderate environmental impact',
                'color': 'warning',
                'icon': 'archive',
                'recommendation': 'Limit consumption and choose options with less added salt, sugar, or oil'
            },
            4: {
                'name': 'Ultra-processed foods',
                'description': 'Industrial formulations made entirely or mostly from substances extracted from foods, derived from food constituents, or synthesized in laboratories.',
                'examples': [
                    'Soft drinks, energy drinks',
                    'Sweet or savory packaged snacks',
                    'Ice cream, chocolate, candies',
                    'Mass-produced packaged breads',
                    'Instant noodles, soups',
                    'Chicken nuggets, hot dogs'
                ],
                'health_impact': 'Poor - Associated with obesity, diabetes, and other health issues',
                'environmental_impact': 'High environmental impact due to processing and packaging',
                'color': 'danger',
                'icon': 'exclamation-triangle',
                'recommendation': 'Avoid or consume very rarely'
            }
        }
        
        if nova_group and nova_group in nova_data:
            return nova_data[nova_group]
        
        return {
            'name': 'Not classified',
            'description': 'NOVA group not determined for this product',
            'examples': [],
            'health_impact': 'Unknown',
            'environmental_impact': 'Unknown',
            'color': 'secondary',
            'icon': 'question-circle',
            'recommendation': 'Check ingredients to determine processing level'
        }
    
    @staticmethod
    def predict_nova_group(ingredients: str, category: str = '') -> int:
        """Predict NOVA group based on ingredients and category"""
        if not ingredients:
            return 1  # Default to unprocessed if no ingredients info
        
        ingredients_lower = ingredients.lower()
        
        # Ultra-processed indicators (Group 4)
        ultra_processed_indicators = [
            'high fructose corn syrup', 'hydrogenated', 'modified starch',
            'artificial flavor', 'artificial color', 'preservative',
            'emulsifier', 'stabilizer', 'thickener', 'anti-caking agent',
            'flavor enhancer', 'sweetener', 'acidity regulator',
            'monosodium glutamate', 'msg', 'sodium benzoate',
            'potassium sorbate', 'calcium propionate'
        ]
        
        # Processed indicators (Group 3)
        processed_indicators = [
            'added sugar', 'added salt', 'oil', 'vinegar',
            'canned', 'smoked', 'cured', 'salted'
        ]
        
        # Check for ultra-processed indicators
        ultra_count = sum(1 for indicator in ultra_processed_indicators 
                         if indicator in ingredients_lower)
        
        if ultra_count >= 2:
            return 4
        elif ultra_count >= 1:
            return 4
        
        # Check for processed indicators
        processed_count = sum(1 for indicator in processed_indicators 
                            if indicator in ingredients_lower)
        
        if processed_count >= 2:
            return 3
        elif processed_count >= 1:
            return 3
        
        # Check ingredient count (more ingredients often means more processed)
        ingredient_count = len([i.strip() for i in ingredients.split(',') if i.strip()])
        
        if ingredient_count > 15:
            return 4
        elif ingredient_count > 8:
            return 3
        elif ingredient_count > 3:
            return 2
        else:
            return 1

# Initialize global predictor instance
eco_predictor = EcoScorePredictor()
nova_analyzer = NovaGroupAnalyzer()
