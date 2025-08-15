"""
Food additives analyzer for identifying and providing information about food additives
"""
import re
from typing import Dict, List, Any, Optional

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
            'E173': {'name': 'Aluminum', 'category': 'Color', 'safety': 'moderate', 'description': 'Metallic silver color'},
            'E174': {'name': 'Silver', 'category': 'Color', 'safety': 'safe', 'description': 'Metallic silver color'},
            'E175': {'name': 'Gold', 'category': 'Color', 'safety': 'safe', 'description': 'Metallic gold color'},
            
            # Preservatives (E200-E299)
            'E200': {'name': 'Sorbic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural preservative, antimicrobial'},
            'E201': {'name': 'Sodium Sorbate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of sorbic acid, antimicrobial'},
            'E202': {'name': 'Potassium Sorbate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of sorbic acid, widely used preservative'},
            'E203': {'name': 'Calcium Sorbate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of sorbic acid'},
            'E210': {'name': 'Benzoic Acid', 'category': 'Preservative', 'safety': 'moderate', 'description': 'Preservative, may cause allergic reactions'},
            'E211': {'name': 'Sodium Benzoate', 'category': 'Preservative', 'safety': 'moderate', 'description': 'Common preservative, may form benzene with vitamin C'},
            'E212': {'name': 'Potassium Benzoate', 'category': 'Preservative', 'safety': 'moderate', 'description': 'Preservative, similar to sodium benzoate'},
            'E213': {'name': 'Calcium Benzoate', 'category': 'Preservative', 'safety': 'moderate', 'description': 'Preservative, benzoate salt'},
            'E220': {'name': 'Sulfur Dioxide', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause asthma attacks'},
            'E221': {'name': 'Sodium Sulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause allergic reactions'},
            'E222': {'name': 'Sodium Bisulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause asthma'},
            'E223': {'name': 'Sodium Metabisulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause severe allergic reactions'},
            'E224': {'name': 'Potassium Metabisulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, similar to E223'},
            'E225': {'name': 'Potassium Sulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause allergic reactions'},
            'E226': {'name': 'Calcium Sulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, sulfite compound'},
            'E227': {'name': 'Calcium Bisulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may cause allergic reactions'},
            'E228': {'name': 'Potassium Bisulfite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, sulfite compound'},
            'E230': {'name': 'Biphenyl', 'category': 'Preservative', 'safety': 'avoid', 'description': 'Fungicide, potential carcinogen'},
            'E231': {'name': 'Orthophenyl Phenol', 'category': 'Preservative', 'safety': 'avoid', 'description': 'Fungicide, potential health risks'},
            'E232': {'name': 'Sodium Orthophenyl Phenol', 'category': 'Preservative', 'safety': 'avoid', 'description': 'Fungicide, potential health risks'},
            'E234': {'name': 'Nisin', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural antimicrobial peptide'},
            'E235': {'name': 'Natamycin', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural antifungal agent'},
            'E239': {'name': 'Hexamethylenetetramine', 'category': 'Preservative', 'safety': 'caution', 'description': 'Preservative, may form formaldehyde'},
            'E242': {'name': 'Dimethyl Dicarbonate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Preservative for beverages'},
            'E249': {'name': 'Potassium Nitrite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Meat preservative, may form nitrosamines'},
            'E250': {'name': 'Sodium Nitrite', 'category': 'Preservative', 'safety': 'caution', 'description': 'Meat preservative, potential carcinogen risk'},
            'E251': {'name': 'Sodium Nitrate', 'category': 'Preservative', 'safety': 'caution', 'description': 'Meat preservative, converts to nitrite'},
            'E252': {'name': 'Potassium Nitrate', 'category': 'Preservative', 'safety': 'caution', 'description': 'Meat preservative, converts to nitrite'},
            'E260': {'name': 'Acetic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Vinegar, natural preservative'},
            'E261': {'name': 'Potassium Acetate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of acetic acid'},
            'E262': {'name': 'Sodium Acetate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of acetic acid'},
            'E263': {'name': 'Calcium Acetate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of acetic acid'},
            'E270': {'name': 'Lactic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural acid, preservative and flavor enhancer'},
            'E280': {'name': 'Propionic Acid', 'category': 'Preservative', 'safety': 'safe', 'description': 'Natural preservative, antimicrobial'},
            'E281': {'name': 'Sodium Propionate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of propionic acid'},
            'E282': {'name': 'Calcium Propionate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Common bread preservative'},
            'E283': {'name': 'Potassium Propionate', 'category': 'Preservative', 'safety': 'safe', 'description': 'Salt of propionic acid'},
            
            # Antioxidants (E300-E399)
            'E300': {'name': 'Ascorbic Acid', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Vitamin C, natural antioxidant'},
            'E301': {'name': 'Sodium Ascorbate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of vitamin C'},
            'E302': {'name': 'Calcium Ascorbate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of vitamin C'},
            'E304': {'name': 'Ascorbyl Palmitate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Fat-soluble form of vitamin C'},
            'E306': {'name': 'Mixed Tocopherols', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Natural vitamin E, excellent antioxidant'},
            'E307': {'name': 'Alpha-tocopherol', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Vitamin E, natural antioxidant'},
            'E308': {'name': 'Gamma-tocopherol', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Form of vitamin E'},
            'E309': {'name': 'Delta-tocopherol', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Form of vitamin E'},
            'E310': {'name': 'Propyl Gallate', 'category': 'Antioxidant', 'safety': 'caution', 'description': 'Synthetic antioxidant, may cause allergic reactions'},
            'E311': {'name': 'Octyl Gallate', 'category': 'Antioxidant', 'safety': 'caution', 'description': 'Synthetic antioxidant, potential allergen'},
            'E312': {'name': 'Dodecyl Gallate', 'category': 'Antioxidant', 'safety': 'caution', 'description': 'Synthetic antioxidant, may cause skin irritation'},
            'E320': {'name': 'BHA', 'category': 'Antioxidant', 'safety': 'avoid', 'description': 'Butylated hydroxyanisole, potential carcinogen'},
            'E321': {'name': 'BHT', 'category': 'Antioxidant', 'safety': 'avoid', 'description': 'Butylated hydroxytoluene, potential health risks'},
            'E322': {'name': 'Lecithin', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Natural emulsifier and antioxidant'},
            'E325': {'name': 'Sodium Lactate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of lactic acid'},
            'E326': {'name': 'Potassium Lactate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of lactic acid'},
            'E327': {'name': 'Calcium Lactate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of lactic acid, calcium supplement'},
            'E330': {'name': 'Citric Acid', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Natural acid from citrus fruits'},
            'E331': {'name': 'Sodium Citrate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of citric acid'},
            'E332': {'name': 'Potassium Citrate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of citric acid'},
            'E333': {'name': 'Calcium Citrate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of citric acid, calcium supplement'},
            'E334': {'name': 'Tartaric Acid', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Natural acid from grapes'},
            'E335': {'name': 'Sodium Tartrate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Salt of tartaric acid'},
            'E336': {'name': 'Potassium Tartrate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Cream of tartar'},
            'E337': {'name': 'Potassium Sodium Tartrate', 'category': 'Antioxidant', 'safety': 'safe', 'description': 'Rochelle salt'},
            
            # Emulsifiers, Stabilizers, Thickeners (E400-E499)
            'E400': {'name': 'Alginic Acid', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural thickener from seaweed'},
            'E401': {'name': 'Sodium Alginate', 'category': 'Thickener', 'safety': 'safe', 'description': 'Salt of alginic acid'},
            'E402': {'name': 'Potassium Alginate', 'category': 'Thickener', 'safety': 'safe', 'description': 'Salt of alginic acid'},
            'E403': {'name': 'Ammonium Alginate', 'category': 'Thickener', 'safety': 'safe', 'description': 'Salt of alginic acid'},
            'E404': {'name': 'Calcium Alginate', 'category': 'Thickener', 'safety': 'safe', 'description': 'Salt of alginic acid'},
            'E405': {'name': 'Propane-1,2-diol Alginate', 'category': 'Thickener', 'safety': 'safe', 'description': 'Modified alginate'},
            'E406': {'name': 'Agar', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gelling agent from seaweed'},
            'E407': {'name': 'Carrageenan', 'category': 'Thickener', 'safety': 'moderate', 'description': 'Natural thickener, may cause digestive issues'},
            'E407a': {'name': 'Processed Eucheuma Seaweed', 'category': 'Thickener', 'safety': 'moderate', 'description': 'Modified carrageenan'},
            'E410': {'name': 'Locust Bean Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural thickener from carob seeds'},
            'E412': {'name': 'Guar Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural thickener from guar beans'},
            'E413': {'name': 'Tragacanth', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gum from plant sap'},
            'E414': {'name': 'Acacia Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gum from acacia trees'},
            'E415': {'name': 'Xanthan Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Microbial thickener, widely used'},
            'E416': {'name': 'Karaya Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gum from trees'},
            'E417': {'name': 'Tara Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural thickener from tara seeds'},
            'E418': {'name': 'Gellan Gum', 'category': 'Thickener', 'safety': 'safe', 'description': 'Microbial gelling agent'},
            'E420': {'name': 'Sorbitol', 'category': 'Sweetener', 'safety': 'moderate', 'description': 'Sugar alcohol, may cause digestive issues'},
            'E421': {'name': 'Mannitol', 'category': 'Sweetener', 'safety': 'moderate', 'description': 'Sugar alcohol, laxative effect'},
            'E422': {'name': 'Glycerol', 'category': 'Humectant', 'safety': 'safe', 'description': 'Natural humectant, keeps food moist'},
            'E440': {'name': 'Pectin', 'category': 'Thickener', 'safety': 'safe', 'description': 'Natural gelling agent from fruits'},
            'E441': {'name': 'Gelatin', 'category': 'Thickener', 'safety': 'safe', 'description': 'Animal-derived gelling agent'},
            'E460': {'name': 'Cellulose', 'category': 'Thickener', 'safety': 'safe', 'description': 'Plant fiber, anti-caking agent'},
            'E461': {'name': 'Methylcellulose', 'category': 'Thickener', 'safety': 'safe', 'description': 'Modified cellulose'},
            'E462': {'name': 'Ethylcellulose', 'category': 'Thickener', 'safety': 'safe', 'description': 'Modified cellulose'},
            'E463': {'name': 'Hydroxypropylcellulose', 'category': 'Thickener', 'safety': 'safe', 'description': 'Modified cellulose'},
            'E464': {'name': 'Hydroxypropylmethylcellulose', 'category': 'Thickener', 'safety': 'safe', 'description': 'Modified cellulose'},
            'E465': {'name': 'Ethylmethylcellulose', 'category': 'Thickener', 'safety': 'safe', 'description': 'Modified cellulose'},
            'E466': {'name': 'Carboxymethylcellulose', 'category': 'Thickener', 'safety': 'safe', 'description': 'Modified cellulose, widely used'},
            'E470a': {'name': 'Sodium Stearate', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Salt of stearic acid'},
            'E470b': {'name': 'Magnesium Stearate', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Salt of stearic acid'},
            'E471': {'name': 'Mono- and Diglycerides', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Common emulsifier from fats'},
            'E472a': {'name': 'Acetic Acid Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Modified mono- and diglycerides'},
            'E472b': {'name': 'Lactic Acid Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Modified mono- and diglycerides'},
            'E472c': {'name': 'Citric Acid Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Modified mono- and diglycerides'},
            'E472d': {'name': 'Tartaric Acid Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Modified mono- and diglycerides'},
            'E472e': {'name': 'Diacetyltartaric Acid Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Bread improver'},
            'E472f': {'name': 'Mixed Acetic and Tartaric Acid Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Modified emulsifier'},
            'E473': {'name': 'Sucrose Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Sugar-based emulsifier'},
            'E474': {'name': 'Sucroglycerides', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Sugar and fat emulsifier'},
            'E475': {'name': 'Polyglycerol Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Complex emulsifier'},
            'E476': {'name': 'Polyglycerol Polyricinoleate', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Chocolate emulsifier'},
            'E477': {'name': 'Propane-1,2-diol Esters', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Synthetic emulsifier'},
            'E481': {'name': 'Sodium Stearoyl Lactylate', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Bread improver'},
            'E482': {'name': 'Calcium Stearoyl Lactylate', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Bread improver'},
            'E483': {'name': 'Stearyl Tartrate', 'category': 'Emulsifier', 'safety': 'safe', 'description': 'Emulsifier for baked goods'},
            
            # Flavor Enhancers (E600-E699)
            'E620': {'name': 'Glutamic Acid', 'category': 'Flavor Enhancer', 'safety': 'safe', 'description': 'Natural amino acid, umami flavor'},
            'E621': {'name': 'Monosodium Glutamate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'MSG, may cause sensitivity in some people'},
            'E622': {'name': 'Monopotassium Glutamate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Similar to MSG'},
            'E623': {'name': 'Calcium Diglutamate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Calcium salt of glutamic acid'},
            'E624': {'name': 'Monoammonium Glutamate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Ammonium salt of glutamic acid'},
            'E625': {'name': 'Magnesium Diglutamate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Magnesium salt of glutamic acid'},
            'E626': {'name': 'Guanylic Acid', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Nucleotide flavor enhancer'},
            'E627': {'name': 'Disodium Guanylate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Often used with MSG'},
            'E628': {'name': 'Dipotassium Guanylate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Potassium salt of guanylic acid'},
            'E629': {'name': 'Calcium Guanylate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Calcium salt of guanylic acid'},
            'E630': {'name': 'Inosinic Acid', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Nucleotide flavor enhancer'},
            'E631': {'name': 'Disodium Inosinate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Often used with MSG'},
            'E632': {'name': 'Dipotassium Inosinate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Potassium salt of inosinic acid'},
            'E633': {'name': 'Calcium Inosinate', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Calcium salt of inosinic acid'},
            'E634': {'name': 'Calcium 5-Ribonucleotides', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Mix of nucleotides'},
            'E635': {'name': 'Disodium 5-Ribonucleotides', 'category': 'Flavor Enhancer', 'safety': 'moderate', 'description': 'Mix of nucleotides, often with MSG'},
            'E640': {'name': 'Glycine', 'category': 'Flavor Enhancer', 'safety': 'safe', 'description': 'Natural amino acid, sweet taste'},
            'E641': {'name': 'L-Leucine', 'category': 'Flavor Enhancer', 'safety': 'safe', 'description': 'Essential amino acid'},
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
            'E230', 'E231', 'E232',  # Fungicides
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
    
    def get_additive_recommendations(self, additives_analysis: Dict[str, Any]) -> List[str]:
        """Get recommendations based on additives analysis"""
        recommendations = []
        
        if additives_analysis['controversial_count'] > 0:
            recommendations.append("Consider products with fewer artificial additives")
        
        if additives_analysis['safety_summary']['avoid'] > 0:
            recommendations.append("Look for alternatives without potentially harmful additives")
        
        if additives_analysis['safety_summary']['caution'] > 2:
            recommendations.append("This product contains multiple additives that may cause sensitivities")
        
        if additives_analysis['total_additives'] > 10:
            recommendations.append("Consider less processed alternatives with fewer additives")
        
        if additives_analysis['health_impact_score'] < 70:
            recommendations.append("Choose products with cleaner ingredient lists when possible")
        
        if not recommendations:
            recommendations.append("This product has a relatively clean additive profile")
        
        return recommendations

class EnvironmentalImpactAnalyzer:
    """
    Analyzer for environmental impact assessment of food products
    """
    
    def __init__(self):
        # Environmental impact factors
        self.packaging_impact = {
            'plastic': {'score': 20, 'recyclable': False, 'biodegradable': False},
            'glass': {'score': 60, 'recyclable': True, 'biodegradable': False},
            'aluminum': {'score': 70, 'recyclable': True, 'biodegradable': False},
            'paper': {'score': 80, 'recyclable': True, 'biodegradable': True},
            'cardboard': {'score': 85, 'recyclable': True, 'biodegradable': True},
            'compostable': {'score': 95, 'recyclable': False, 'biodegradable': True},
        }
        
        # Ingredient environmental impact
        self.ingredient_impact = {
            # High impact ingredients
            'palm oil': {'score': 10, 'reason': 'Deforestation and habitat destruction'},
            'beef': {'score': 15, 'reason': 'High greenhouse gas emissions'},
            'lamb': {'score': 20, 'reason': 'High greenhouse gas emissions'},
            'cheese': {'score': 30, 'reason': 'High water usage and emissions'},
            'butter': {'score': 35, 'reason': 'High emissions from dairy production'},
            'milk': {'score': 40, 'reason': 'Moderate emissions from dairy production'},
            
            # Moderate impact ingredients
            'chicken': {'score': 50, 'reason': 'Moderate emissions from poultry'},
            'eggs': {'score': 55, 'reason': 'Moderate emissions from poultry'},
            'fish': {'score': 60, 'reason': 'Varies by fishing method'},
            'pork': {'score': 45, 'reason': 'Moderate to high emissions'},
            
            # Low impact ingredients
            'vegetables': {'score': 90, 'reason': 'Low emissions and water usage'},
            'fruits': {'score': 85, 'reason': 'Generally low environmental impact'},
            'grains': {'score': 80, 'reason': 'Efficient land use'},
            'legumes': {'score': 95, 'reason': 'Nitrogen fixing, very sustainable'},
            'nuts': {'score': 70, 'reason': 'Moderate water usage'},
            'seeds': {'score': 85, 'reason': 'Generally sustainable'},
            
            # Plant-based alternatives
            'soy': {'score': 75, 'reason': 'Efficient protein source'},
            'oats': {'score': 90, 'reason': 'Very sustainable grain'},
            'rice': {'score': 60, 'reason': 'High water usage and methane emissions'},
            'quinoa': {'score': 70, 'reason': 'Sustainable but water-intensive'},
        }
        
        # Processing level impact
        self.processing_impact = {
            1: {'score': 90, 'description': 'Minimal processing, low environmental impact'},
            2: {'score': 75, 'description': 'Basic processing, moderate impact'},
            3: {'score': 50, 'description': 'Processed foods, higher energy use'},
            4: {'score': 25, 'description': 'Ultra-processed, high environmental impact'},
        }
        
        # Transportation impact indicators
        self.transport_keywords = {
            'local': {'score': 90, 'description': 'Locally sourced'},
            'organic': {'score': 80, 'description': 'Organic farming practices'},
            'fair trade': {'score': 85, 'description': 'Sustainable trade practices'},
            'sustainable': {'score': 85, 'description': 'Sustainable sourcing'},
            'imported': {'score': 30, 'description': 'Long-distance transportation'},
            'air freight': {'score': 10, 'description': 'High-emission transportation'},
        }
    
    def analyze_environmental_impact(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze environmental impact of a product
        """
        ingredients = product_data.get('ingredients', '').lower()
        category = product_data.get('category', '').lower()
        nova_group = product_data.get('nova_group', 3)
        brand = product_data.get('brand', '').lower()
        
        # Analyze different impact factors
        ingredient_score = self._analyze_ingredient_impact(ingredients)
        processing_score = self._analyze_processing_impact(nova_group)
        transport_score = self._analyze_transport_impact(ingredients, brand)
        packaging_score = self._estimate_packaging_impact(category)
        
        # Calculate overall environmental score (weighted average)
        overall_score = (
            ingredient_score['score'] * 0.4 +
            processing_score['score'] * 0.3 +
            transport_score['score'] * 0.2 +
            packaging_score['score'] * 0.1
        )
        
        # Generate recommendations
        recommendations = self._generate_environmental_recommendations(
            ingredient_score, processing_score, transport_score, packaging_score
        )
        
        return {
            'overall_score': round(overall_score),
            'grade': self._score_to_grade(overall_score),
            'ingredient_impact': ingredient_score,
            'processing_impact': processing_score,
            'transport_impact': transport_score,
            'packaging_impact': packaging_score,
            'recommendations': recommendations,
            'carbon_footprint_estimate': self._estimate_carbon_footprint(overall_score),
            'water_usage_estimate': self._estimate_water_usage(ingredient_score),
        }
    
    def _analyze_ingredient_impact(self, ingredients: str) -> Dict[str, Any]:
        """Analyze environmental impact of ingredients"""
        if not ingredients:
            return {'score': 70, 'details': [], 'high_impact_count': 0}
        
        details = []
        scores = []
        high_impact_count = 0
        
        for ingredient, impact in self.ingredient_impact.items():
            if ingredient in ingredients:
                details.append({
                    'ingredient': ingredient.title(),
                    'score': impact['score'],
                    'reason': impact['reason'],
                    'impact_level': 'high' if impact['score'] < 50 else 'moderate' if impact['score'] < 75 else 'low'
                })
                scores.append(impact['score'])
                
                if impact['score'] < 50:
                    high_impact_count += 1
        
        # If no specific ingredients found, estimate based on category
        if not scores:
            scores = [70]  # Default moderate score
        
        avg_score = sum(scores) / len(scores)
        
        return {
            'score': round(avg_score),
            'details': details,
            'high_impact_count': high_impact_count
        }
    
    def _analyze_processing_impact(self, nova_group: int) -> Dict[str, Any]:
        """Analyze environmental impact of processing level"""
        if nova_group in self.processing_impact:
            impact = self.processing_impact[nova_group]
            return {
                'score': impact['score'],
                'level': nova_group,
                'description': impact['description']
            }
        
        return {
            'score': 50,
            'level': 3,
            'description': 'Processing level unknown'
        }
    
    def _analyze_transport_impact(self, ingredients: str, brand: str) -> Dict[str, Any]:
        """Analyze transportation impact"""
        combined_text = f"{ingredients} {brand}"
        
        for keyword, impact in self.transport_keywords.items():
            if keyword in combined_text:
                return {
                    'score': impact['score'],
                    'indicator': keyword.title(),
                    'description': impact['description']
                }
        
        # Default assumption for unknown transport
        return {
            'score': 60,
            'indicator': 'Unknown',
            'description': 'Transportation impact unknown'
        }
    
    def _estimate_packaging_impact(self, category: str) -> Dict[str, Any]:
        """Estimate packaging impact based on product category"""
        # Simple estimation based on common packaging for categories
        if any(word in category for word in ['beverage', 'drink', 'juice']):
            return {'score': 40, 'type': 'Mixed (plastic/glass)', 'recyclable': True}
        elif any(word in category for word in ['canned', 'tin']):
            return {'score': 70, 'type': 'Aluminum', 'recyclable': True}
        elif any(word in category for word in ['fresh', 'produce']):
            return {'score': 85, 'type': 'Minimal packaging', 'recyclable': True}
        elif any(word in category for word in ['frozen', 'packaged']):
            return {'score': 30, 'type': 'Plastic packaging', 'recyclable': False}
        else:
            return {'score': 50, 'type': 'Mixed packaging', 'recyclable': True}
    
    def _generate_environmental_recommendations(self, ingredient_score, processing_score, transport_score, packaging_score) -> List[str]:
        """Generate environmental recommendations"""
        recommendations = []
        
        if ingredient_score['high_impact_count'] > 0:
            recommendations.append("Consider plant-based alternatives to reduce environmental impact")
        
        if processing_score['score'] < 50:
            recommendations.append("Choose less processed foods to reduce energy consumption")
        
        if transport_score['score'] < 60:
            recommendations.append("Look for locally sourced or organic alternatives")
        
        if packaging_score['score'] < 50:
            recommendations.append("Choose products with recyclable or minimal packaging")
        
        if not recommendations:
            recommendations.append("This product has a relatively good environmental profile")
        
        return recommendations
    
    def _score_to_grade(self, score: float) -> str:
        """Convert environmental score to letter grade"""
        if score >= 80:
            return 'A'
        elif score >= 65:
            return 'B'
        elif score >= 50:
            return 'C'
        elif score >= 35:
            return 'D'
        else:
            return 'E'
    
    def _estimate_carbon_footprint(self, score: float) -> str:
        """Estimate carbon footprint category"""
        if score >= 80:
            return 'Very Low'
        elif score >= 65:
            return 'Low'
        elif score >= 50:
            return 'Moderate'
        elif score >= 35:
            return 'High'
        else:
            return 'Very High'
    
    def _estimate_water_usage(self, ingredient_score: Dict[str, Any]) -> str:
        """Estimate water usage based on ingredients"""
        score = ingredient_score['score']
        if score >= 80:
            return 'Low'
        elif score >= 60:
            return 'Moderate'
        else:
            return 'High'

# Initialize global analyzers
additives_analyzer = AdditivesAnalyzer()
environmental_analyzer = EnvironmentalImpactAnalyzer()
