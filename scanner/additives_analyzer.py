"""
Food additives analyzer for identifying and providing information about food additives
"""
import re
from typing import Dict, List, Any, Optional

def analyze_additives(ingredients: str) -> Dict[str, Any]:
    """
    Main function to analyze additives in ingredients text
    """
    if not ingredients:
        return {
            'total_additives': 0,
            'controversial_count': 0,
            'health_impact_score': 100,
            'overall_assessment': 'No additives detected',
            'safety_summary': {'safe': 0, 'moderate': 0, 'avoid': 0},
            'detailed_additives': [],
            'main_concerns': []
        }
    
    analyzer = AdditivesAnalyzer()
    analysis = analyzer.analyze_ingredients(ingredients)
    
    # Convert to format expected by template
    detailed_additives = []
    main_concerns = []
    
    for additive in analysis['additives_found']:
        detailed_additive = {
            'code': additive['e_number'],
            'name': additive['name'],
            'function': additive['category'],
            'description': additive['description'],
            'safety_level': additive['safety'],
            'health_effects': get_health_effects(additive['e_number']),
            'sources': get_common_sources(additive['category']),
            'recommendation': get_recommendation(additive['safety'])
        }
        detailed_additives.append(detailed_additive)
        
        # Add to main concerns if problematic
        if additive['safety'] in ['avoid', 'caution'] and additive.get('controversial', False):
            main_concerns.append(f"{additive['name']} ({additive['e_number']})")
    
    # Generate overall assessment
    overall_assessment = generate_overall_assessment(analysis)
    
    return {
        'total_additives': analysis['total_additives'],
        'controversial_count': analysis['controversial_count'],
        'health_impact_score': analysis['health_impact_score'],
        'overall_assessment': overall_assessment,
        'safety_summary': analysis['safety_summary'],
        'detailed_additives': detailed_additives,
        'main_concerns': main_concerns[:3]  # Limit to top 3 concerns
    }

def get_health_effects(e_number: str) -> str:
    """Get health effects description for an E-number"""
    health_effects = {
        'E102': 'May cause hyperactivity in children, especially when combined with benzoates',
        'E110': 'Linked to hyperactivity and attention problems in children',
        'E124': 'May cause hyperactivity, asthma, and skin reactions',
        'E129': 'Associated with hyperactivity in children and may cause allergic reactions',
        'E171': 'Potential concerns about nanoparticles and gut health',
        'E250': 'May form nitrosamines (potential carcinogens) when combined with certain proteins',
        'E320': 'Potential endocrine disruptor and possible carcinogen',
        'E321': 'May cause allergic reactions and potential health concerns',
        'E621': 'Some people experience MSG sensitivity symptoms like headaches',
        'E220': 'Can trigger asthma attacks and allergic reactions in sensitive individuals',
    }
    return health_effects.get(e_number, 'Generally recognized as safe when used within approved limits')

def get_common_sources(category: str) -> str:
    """Get common food sources for additive categories"""
    sources = {
        'Color': 'Candies, beverages, baked goods, processed foods',
        'Preservative': 'Processed meats, canned foods, beverages, baked goods',
        'Antioxidant': 'Oils, fats, processed foods, supplements',
        'Thickener': 'Sauces, dairy products, baked goods, processed foods',
        'Emulsifier': 'Margarine, ice cream, chocolate, baked goods',
        'Flavor Enhancer': 'Savory snacks, soups, processed meats, Asian cuisine',
        'Sweetener': 'Diet foods, sugar-free products, chewing gum'
    }
    return sources.get(category, 'Various processed foods')

def get_recommendation(safety_level: str) -> str:
    """Get recommendation based on safety level"""
    recommendations = {
        'safe': 'Generally safe for consumption within normal dietary intake',
        'moderate': 'Use in moderation, may cause sensitivity in some individuals',
        'caution': 'Consider limiting intake, especially for children and sensitive individuals',
        'avoid': 'Consider avoiding or choosing alternatives when possible'
    }
    return recommendations.get(safety_level, 'Consult with healthcare provider if concerned')

def generate_overall_assessment(analysis: Dict[str, Any]) -> str:
    """Generate overall assessment text"""
    score = analysis['health_impact_score']
    total = analysis['total_additives']
    controversial = analysis['controversial_count']
    
    if score >= 80:
        return f"This product contains {total} additive{'s' if total != 1 else ''} with a good safety profile."
    elif score >= 60:
        return f"This product contains {total} additive{'s' if total != 1 else ''} with moderate safety concerns."
    elif score >= 40:
        return f"This product contains {total} additive{'s' if total != 1 else ''}, including {controversial} controversial one{'s' if controversial != 1 else ''}."
    else:
        return f"This product contains {total} additive{'s' if total != 1 else ''} with significant safety concerns."

class AdditivesAnalyzer:
    """
    Comprehensive food additives analyzer with E-number identification and health impact assessment
    """
    
    def __init__(self):
        # Comprehensive E-number database with health impact ratings
        self.e_numbers = {
            # Colors (E100-E199)
            'E100': {'name': 'Curcumin', 'category': 'Color', 'safety': 'safe', 'description': 'Natural yellow color from turmeric'},
            'E101': {'name': 'Riboflavin', 'category': 'Color', 'safety': 'safe', 'description': 'Vitamin B2, natural yellow color'},
            'E102': {'name': 'Tartrazine', 'category': 'Color', 'safety': 'caution', 'description': 'Synthetic yellow dye, may cause hyperactivity in children'},
            'E104': {'name': 'Quinoline Yellow', 'category': 'Color', 'safety': 'caution', 'description': 'Synthetic yellow dye, may cause allergic reactions'},
            'E110': {'name': 'Sunset Yellow', 'category': 'Color', 'safety': 'caution', 'description': 'Synthetic orange dye, linked to hyperactivity'},
            'E120': {'name': 'Cochineal', 'category': 'Color', 'safety': 'moderate', 'description': 'Natural red color from insects, may cause allergies'},
            'E122': {'name': 'Azorubine', 'category': 'Color', 'safety': 'caution', 'description': 'Synthetic red dye, may cause hyperactivity'},
            'E123': {'name': 'Amaranth', 'category': 'Color', 'safety': 'avoid', 'description': 'Synthetic red dye, banned in some countries'},
            'E124': {'name': 'Ponceau 4R', 'category': 'Color', 'safety': 'caution', 'description': 'Synthetic red dye, may cause hyperactivity'},
            'E129': {'name': 'Allura Red', 'category': 'Color', 'safety': 'caution', 'description': 'Synthetic red dye, may cause hyperactivity'},
            'E131': {'name': 'Patent Blue V', 'category': 'Color', 'safety': 'moderate', 'description': 'Synthetic blue dye, may cause allergic reactions'},
            'E132': {'name': 'Indigo Carmine', 'category': 'Color', 'safety': 'moderate', 'description': 'Synthetic blue dye'},
            'E133': {'name': 'Brilliant Blue', 'category': 'Color', 'safety': 'safe', 'description': 'Synthetic blue dye, generally safe'},
            'E140': {'name': 'Chlorophyll', 'category': 'Color', 'safety': 'safe', 'description': 'Natural green color from plants'},
            'E141': {'name': 'Copper Chlorophyll', 'category': 'Color', 'safety': 'safe', 'description': 'Modified natural green color'},
            'E150a': {'name': 'Caramel I', 'category': 'Color', 'safety': 'safe', 'description': 'Plain caramel, natural brown color'},
            'E150b': {'name': 'Caramel II', 'category': 'Color', 'safety': 'safe', 'description': 'Caustic sulfite caramel'},
            'E150c': {'name': 'Caramel III', 'category': 'Color', 'safety': 'moderate', 'description': 'Ammonia caramel'},
            'E150d': {'name': 'Caramel IV', 'category': 'Color', 'safety': 'moderate', 'description': 'Sulfite ammonia caramel'},
            'E160a': {'name': 'Beta-carotene', 'category': 'Color', 'safety': 'safe', 'description': 'Natural orange color, vitamin A precursor'},
            'E160b': {'name': 'Annatto', 'category': 'Color', 'safety': 'safe', 'description': 'Natural orange-red color from seeds'},
            'E160c': {'name': 'Paprika Extract', 'category': 'Color', 'safety': 'safe', 'description': 'Natural red color from paprika'},
            'E161b': {'name': 'Lutein', 'category': 'Color', 'safety': 'safe', 'description': 'Natural yellow color, antioxidant'},
            'E162': {'name': 'Beetroot Red', 'category': 'Color', 'safety': 'safe', 'description': 'Natural red color from beetroot'},
            'E163': {'name': 'Anthocyanins', 'category': 'Color', 'safety': 'safe', 'description': 'Natural purple/red colors from fruits'},
            'E170': {'name': 'Calcium Carbonate', 'category': 'Color', 'safety': 'safe', 'description': 'Natural white color, calcium supplement'},
            'E171': {'name': 'Titanium Dioxide', 'category': 'Color', 'safety': 'caution', 'description': 'White color, potential health concerns'},
            'E172': {'name': 'Iron Oxides', 'category': 'Color', 'safety': 'safe', 'description': 'Natural mineral colors (red, yellow, black)'},
            
            # Preservatives (E200-E299)
            'E200': {'name': 'Sorbic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural preservative, antimicrobial'},
            'E201': {'name': 'Sodium Sorbate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of sorbic acid, antimicrobial'},
            'E202': {'name': 'Potassium Sorbate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of sorbic acid, widely used preservative'},
            'E210': {'name': 'Benzoic Acid', 'category': 'Preservative', 'safety': 'moderate', 'description': 'Preservative, may cause allergic reactions'},
            'E211': {'name': 'Sodium Benzoate', 'category': 'Preservative', 'safety': 'moderate', 'description': 'Common preservative, may form benzene with vitamin C'},
            'E220': {'name': 'Sulfur Dioxide', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause asthma attacks'},
            'E221': {'name': 'Sodium Sulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause allergic reactions'},
            'E250': {'name': 'Sodium Nitrite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Meat preservative, potential carcinogen risk'},
            'E251': {'name': 'Sodium Nitrate', 'category': 'Preservative', 'safety': 'caution', 'description': 'Meat preservative, converts to nitrite'},
            'E260': {'name': 'Acetic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Vinegar, natural preservative'},
            'E270': {'name': 'Lactic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural acid, preservative and flavor enhancer'},
            'E280': {'name': 'Propionic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural preservative, antimicrobial'},
            'E282': {'name': 'Calcium Propionate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Common bread preservative'},
            
            # Antioxidants (E300-E399)
            'E300': {'name': 'Ascorbic Acid', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Vitamin C, natural antioxidant'},
            'E301': {'name': 'Sodium Ascorbate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of vitamin C'},
            'E306': {'name': 'Mixed Tocopherols', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Natural vitamin E, excellent antioxidant'},
            'E307': {'name': 'Alpha-tocopherol', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Vitamin E, natural antioxidant'},
            'E320': {'name': 'BHA', 'category': 'Antioxidant', 'safety': 'avoid', 'description': 'Butylated hydroxyanisole, potential carcinogen'},
            'E321': {'name': 'BHT', 'category': 'Antioxidant', 'safety': 'avoid', 'description': 'Butylated hydroxytoluene, potential health risks'},
            'E322': {'name': 'Lecithin', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Natural emulsifier and antioxidant'},
            'E330': {'name': 'Citric Acid', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Natural acid from citrus fruits'},
            'E331': {'name': 'Sodium Citrate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of citric acid'},
            
            # Emulsifiers, Stabilizers, Thickeners (E400-E499)
            'E406': {'name': 'Agar', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gelling agent from seaweed'},
            'E407': {'name': 'Carrageenan', 'category': 'Thickener', 'safety': 'moderate', 'description': 'Natural thickener, may cause digestive issues'},
            'E410': {'name': 'Locust Bean Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural thickener from carob seeds'},
            'E412': {'name': 'Guar Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural thickener from guar beans'},
            'E414': {'name': 'Acacia Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gum from acacia trees'},
            'E415': {'name': 'Xanthan Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Microbial thickener, widely used'},
            'E440': {'name': 'Pectin', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gelling agent from fruits'},
            'E471': {'name': 'Mono- and Diglycerides', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Common emulsifier from fats'},
            
            # Flavor Enhancers (E600-E699)
            'E620': {'name': 'Glutamic Acid', 'category': 'Flavor Enhancer', 'safety': 'safe', 'description': 'Natural amino acid, umami flavor'},
            'E621': {'name': 'Monosodium Glutamate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'MSG, may cause sensitivity in some people'},
            'E627': {'name': 'Disodium Guanylate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Often used with MSG'},
            'E631': {'name': 'Disodium Inosinate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Often used with MSG'},
            'E635': {'name': 'Disodium 5-Ribonucleotides', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Mix of nucleotides, often with MSG'},
        }
        
        # Common additive names and their E-numbers
        self.common_names = {
            'msg': 'E621',
            'monosodium glutamate': 'E621',
            'vitamin c': 'E300',
            'ascorbic acid': 'E300',
            'citric acid': 'E330',
            'lecithin': 'E322',
            'xanthan gum': 'E415',
            'guar gum': 'E412',
            'carrageenan': 'E407',
            'sodium benzoate': 'E211',
            'potassium sorbate': 'E202',
            'sodium nitrite': 'E250',
            'sodium nitrate': 'E251',
            'bha': 'E320',
            'bht': 'E321',
            'tartrazine': 'E102',
            'sunset yellow': 'E110',
            'allura red': 'E129',
            'brilliant blue': 'E133',
            'titanium dioxide': 'E171',
            'caramel color': 'E150a',
            'beta carotene': 'E160a',
            'annatto': 'E160b',
        }
        
        # Controversial additives that should be highlighted
        self.controversial = [
            'E102', 'E104', 'E110', 'E122', 'E123', 'E124', 'E129',  # Artificial colors
            'E171',  # Titanium dioxide
            'E320', 'E321',  # BHA, BHT
            'E220', 'E221', 'E222', 'E223', 'E224', 'E225', 'E226', 'E227', 'E228',  # Sulfites
            'E249', 'E250', 'E251', 'E252',  # Nitrites/Nitrates
            'E621', 'E622', 'E623', 'E624', 'E625',  # MSG and related
        ]
    
    def analyze_ingredients(self, ingredients: str) -> Dict[str, Any]:
        """
        Analyze ingredients text for additives and provide comprehensive information
        """
        if not ingredients:
            return {
                'additives_found': [],
                'total_additives': 0,
                'safety_summary': {'safe': 0, 'moderate': 0, 'caution': 0, 'avoid': 0},
                'categories': {},
                'controversial_count': 0,
                'health_impact_score': 100
            }
        
        ingredients_lower = ingredients.lower()
        additives_found = []
        
        # Find E-numbers
        e_numbers = re.findall(r'e\d{3}[a-z]?', ingredients_lower)
        for e_num in e_numbers:
            e_upper = e_num.upper()
            if e_upper in self.e_numbers:
                additive_info = self.e_numbers[e_upper].copy()
                additive_info['e_number'] = e_upper
                additive_info['found_as'] = e_num
                additives_found.append(additive_info)
        
        # Find common names
        for common_name, e_number in self.common_names.items():
            if common_name in ingredients_lower and e_number in self.e_numbers:
                # Check if we already found this additive by E-number
                if not any(add['e_number'] == e_number for add in additives_found):
                    additive_info = self.e_numbers[e_number].copy()
                    additive_info['e_number'] = e_number
                    additive_info['found_as'] = common_name
                    additives_found.append(additive_info)
        
        # Calculate statistics
        safety_summary = {'safe': 0, 'moderate': 0, 'caution': 0, 'avoid': 0}
        categories = {}
        controversial_count = 0
        
        for additive in additives_found:
            safety = additive['safety']
            category = additive['category']
            e_number = additive['e_number']
            
            safety_summary[safety] += 1
            categories[category] = categories.get(category, 0) + 1
            
            if e_number in self.controversial:
                controversial_count += 1
                additive['controversial'] = True
            else:
                additive['controversial'] = False
        
        # Calculate health impact score
        health_impact_score = self._calculate_health_impact_score(safety_summary, controversial_count)
        
        return {
            'additives_found': additives_found,
            'total_additives': len(additives_found),
            'safety_summary': safety_summary,
            'categories': categories,
            'controversial_count': controversial_count,
            'health_impact_score': health_impact_score
        }
    
    def _calculate_health_impact_score(self, safety_summary: Dict[str, int], controversial_count: int) -> int:
        """Calculate health impact score based on additive safety"""
        base_score = 100
        
        # Deduct points based on safety levels
        base_score -= safety_summary['avoid'] * 20
        base_score -= safety_summary['caution'] * 10
        base_score -= safety_summary['moderate'] * 5
        # Safe additives don't reduce score
        
        # Additional penalty for controversial additives
        base_score -= controversial_count * 5
        
        return max(0, min(100, base_score))
