import cv2
import numpy as np
import requests
import pytesseract
import re
from PIL import Image
import io
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from scanner.models import Product, ScanHistory, NutritionFact, Review
from accounts.models import CustomUser, FavoriteProduct, ProductReview
import logging
from pyzbar.pyzbar import decode

# Configure logging
logger = logging.getLogger(__name__)

# Configure Tesseract (update path as needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def index(request):
    """Scanner home page"""
    return render(request, 'scanner/index.html')

@login_required
def product_detail(request, barcode):
    try:
        product = get_object_or_404(Product, barcode=barcode)
        
        # Calculate health score if not already set
        if product.health_score is None and product.nutrition_info:
            product.health_score = product.calculate_health_score()
            product.save()
        
        # Prepare dietary flags with enhanced visual indicators
        dietary_flags = []
        
        dietary_flags.append({
            'type': 'vegan', 'status': product.vegan,
            'label': 'Vegan' if product.vegan else 'Not Vegan',
            'color': 'success' if product.vegan else 'danger',
            'icon': '✅' if product.vegan else '❌'
        })
        dietary_flags.append({
            'type': 'vegetarian', 'status': product.vegetarian,
            'label': 'Vegetarian' if product.vegetarian else 'Not Vegetarian',
            'color': 'success' if product.vegetarian else 'danger',
            'icon': '✅' if product.vegetarian else '❌'
        })
        dietary_flags.append({
            'type': 'palm_oil', 'status': product.palm_oil_free,
            'label': 'Palm Oil Free' if product.palm_oil_free else 'Contains Palm Oil',
            'color': 'success' if product.palm_oil_free else 'danger',
            'icon': '✅' if product.palm_oil_free else '⚠️'
        })
        
        # Parse nutrition facts
        nutrition_facts = parse_nutrition_facts(product.nutrition_info) if product.nutrition_info else []
        
        # Check for existing review by the current user
        existing_review = None
        is_favorite = False
        if request.user.is_authenticated:
            try:
                existing_review = product.productreview_set.get(user=request.user)
            except:
                existing_review = None
            
            is_favorite = FavoriteProduct.objects.filter(user=request.user, product=product).exists()

        return render(request, 'scanner/product.html', {
            'product': product,
            'nutrition_facts': nutrition_facts,
            'dietary_flags': dietary_flags,
            'existing_review': existing_review,
            'is_favorite': is_favorite,
        })
        
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        return redirect('scanner:index')

@login_required
def scan_barcode(request):
    context = {}
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            img = process_uploaded_image(image_file)
            
            if img is None:
                messages.error(request, 'Invalid image format or corrupted file.')
                return render(request, 'scanner/scan.html', {'error': 'Invalid image format'})
            
            barcode_result = detect_barcode_enhanced(img)
            
            if not barcode_result:
                messages.warning(request, 'No valid barcode detected. Please ensure the barcode is clearly visible and well-lit.')
                return render(request, 'scanner/scan.html', {
                    'error': 'No valid barcode detected. Please ensure the barcode is clearly visible and well-lit.',
                    'allow_manual': True,
                    'tips': [
                        'Make sure the barcode is in focus',
                        'Ensure good lighting',
                        'Try different angles',
                        'Clean the camera lens'
                    ]
                })
            
            barcode = barcode_result['code']
            barcode_type = barcode_result['type']
            
            logger.info(f"Detected {barcode_type} barcode: {barcode}")
            
            try:
                product = Product.objects.get(barcode=barcode)
                messages.info(request, f'Product "{product.name}" found in your database.')
                if request.user.is_authenticated:
                    ScanHistory.objects.create(user=request.user, product=product)
                    logger.info(f"Recorded scan for user {request.user.username}: {barcode}")
                return redirect('scanner:product_detail', barcode=barcode)
            except Product.DoesNotExist:
                pass
            
            product_info = fetch_product_info_enhanced(barcode, barcode_type)
            
            if not product_info:
                messages.error(request, 'Product not found in any external database.')
                return render(request, 'scanner/scan.html', {
                    'error': 'Product not found in any database.',
                    'barcode': barcode,
                    'barcode_type': barcode_type,
                    'suggest_url': f'https://world.openfoodfacts.org/product/{barcode}',
                    'allow_manual': True
                })
            
            product = save_product(barcode, product_info, barcode_type)
            messages.success(request, f'Product "{product.name}" successfully added and scanned!')
            if request.user.is_authenticated:
                ScanHistory.objects.create(user=request.user, product=product)
                logger.info(f"Recorded scan for user {request.user.username}: {barcode}")
            return redirect('scanner:product_detail', barcode=barcode)
            
        except Exception as e:
            logger.error(f"Error processing barcode scan: {str(e)}")
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return render(request, 'scanner/scan.html', {
                'error': f'Error processing your request: {str(e)}',
                'allow_manual': True
            })
    
    return render(request, 'scanner/scan.html')

def scan(request):
    """Legacy scan view for compatibility"""
    return scan_barcode(request)

@login_required
def manual_entry(request):
    """Enhanced manual entry with better validation"""
    if request.method == 'POST':
        barcode = request.POST.get('barcode', '').strip()
        
        if not barcode.isdigit():
            return render(request, 'scanner/scan.html', {
                'error': 'Barcode must contain only numbers.',
                'allow_manual': True
            })
        
        if not (8 <= len(barcode) <= 14):
            return render(request, 'scanner/scan.html', {
                'error': 'Barcode must be between 8 and 14 digits long.',
                'allow_manual': True
            })
        
        try:
            product = Product.objects.get(barcode=barcode)
            return redirect('scanner:product_detail', barcode=barcode)
        except Product.DoesNotExist:
            pass
        
        product_info = fetch_product_info_enhanced(barcode, 'manual')
        
        if product_info:
            product = save_product(barcode, product_info, 'manual')
            return redirect('scanner:product_detail', barcode=barcode)
        else:
            return render(request, 'scanner/scan.html', {
                'error': 'Product not found in any database.',
                'barcode': barcode,
                'suggest_url': f'https://world.openfoodfacts.org/product/{barcode}',
                'allow_manual': True
            })
    
    return redirect('scanner:scan')

@login_required
def submit_review(request, barcode):
    if request.method == 'POST':
        product = get_object_or_404(Product, barcode=barcode)
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        if rating:
            ProductReview.objects.update_or_create(
                user=request.user,
                product=product,
                defaults={
                    'rating': int(rating),
                    'review_text': review_text or ''
                }
            )
            messages.success(request, 'Your review has been submitted!')
        
    return redirect('scanner:product_detail', barcode=barcode)

@login_required
def toggle_favorite(request, barcode):
    """Toggle favorite status for a product"""
    if request.method == 'POST':
        product = get_object_or_404(Product, barcode=barcode)
        favorite, created = FavoriteProduct.objects.get_or_create(
            user=request.user, 
            product=product
        )
        
        if not created:
            favorite.delete()
            messages.info(request, f'"{product.name}" removed from favorites.')
        else:
            messages.success(request, f'"{product.name}" added to favorites!')
    
    return redirect('scanner:product_detail', barcode=barcode)

def search_products(request):
    """Search products"""
    query = request.GET.get('q', '')
    products = []
    
    if query:
        from django.db.models import Q
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(brand__icontains=query) |
            Q(barcode__icontains=query)
        ).order_by('name')[:20]
    
    context = {
        'products': products,
        'query': query,
    }
    return render(request, 'scanner/search.html', context)

@login_required
def scan_history(request):
    """User's scan history"""
    history = ScanHistory.objects.filter(user=request.user).select_related('product').order_by('-scanned_at')
    
    context = {
        'history': history,
    }
    return render(request, 'scanner/history.html', context)

# Helper functions
def process_uploaded_image(image_file):
    """Process uploaded image for barcode detection"""
    try:
        image = Image.open(image_file)
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return None

def detect_barcode_enhanced(img):
    """Enhanced barcode detection"""
    try:
        barcodes = decode(img)
        if barcodes:
            barcode = barcodes[0]
            return {
                'code': barcode.data.decode('utf-8'),
                'type': barcode.type
            }
    except Exception as e:
        logger.error(f"Barcode detection error: {e}")
    
    return None

def fetch_product_info_enhanced(barcode, barcode_type):
    """Enhanced product info fetching"""
    try:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data.get('status') == 1:
            product = data.get('product', {})
            return {
                'name': product.get('product_name', f'Product {barcode}'),
                'brand': product.get('brands', ''),
                'category': product.get('categories', ''),
                'ingredients': product.get('ingredients_text', ''),
                'nutrition': product.get('nutriments', {}),
                'image_url': product.get('image_url', ''),
                'ecoscore': product.get('ecoscore_grade', '').upper(),
                'nova_group': product.get('nova_group'),
                'source': 'openfoodfacts'
            }
    except Exception as e:
        logger.error(f"API error: {e}")
    
    return None

def save_product(barcode, product_info, barcode_type):
    """Save product to database"""
    ingredients = product_info.get('ingredients', '')
    
    product = Product(
        barcode=barcode,
        name=product_info['name'],
        brand=product_info.get('brand', ''),
        category=product_info.get('category', ''),
        ingredients=ingredients,
        nutrition_info=product_info.get('nutrition', {}),
        image_url=product_info.get('image_url', ''),
        ecoscore=product_info.get('ecoscore', ''),
        nova_group=product_info.get('nova_group'),
        vegan=analyze_if_vegan(ingredients),
        vegetarian=analyze_if_vegetarian(ingredients),
        palm_oil_free=analyze_if_palm_oil_free(ingredients)
    )
    
    product.health_score = product.calculate_health_score()
    product.allergens = product.detect_allergens()
    product.save()
    
    return product

def parse_nutrition_facts(nutrition_info):
    """Parse nutrition information into display format"""
    if not nutrition_info:
        return []
    
    facts = []
    nutrition_mapping = {
        'energy-kcal': {'name': 'Energy', 'unit': 'kcal'},
        'fat': {'name': 'Fat', 'unit': 'g'},
        'saturated-fat': {'name': 'Saturated Fat', 'unit': 'g'},
        'carbohydrates': {'name': 'Carbohydrates', 'unit': 'g'},
        'sugars': {'name': 'Sugars', 'unit': 'g'},
        'proteins': {'name': 'Proteins', 'unit': 'g'},
        'salt': {'name': 'Salt', 'unit': 'g'},
        'fiber': {'name': 'Fiber', 'unit': 'g'},
    }
    
    for key, info in nutrition_mapping.items():
        if key in nutrition_info:
            value = nutrition_info[key]
            if isinstance(value, (int, float)):
                facts.append({
                    'name': info['name'],
                    'value': round(value, 1),
                    'unit': info['unit'],
                    'percentage': min(100, (value / 50) * 100) if info['unit'] == 'g' else None
                })
    
    return facts

def analyze_if_vegan(ingredients):
    """Analyze if product is vegan"""
    if not ingredients:
        return None
    
    non_vegan_keywords = ['milk', 'egg', 'honey', 'meat', 'fish', 'chicken', 'beef', 'pork']
    ingredients_lower = ingredients.lower()
    
    for keyword in non_vegan_keywords:
        if keyword in ingredients_lower:
            return False
    
    return True

def analyze_if_vegetarian(ingredients):
    """Analyze if product is vegetarian"""
    if not ingredients:
        return None
    
    non_vegetarian_keywords = ['meat', 'fish', 'chicken', 'beef', 'pork', 'gelatin']
    ingredients_lower = ingredients.lower()
    
    for keyword in non_vegetarian_keywords:
        if keyword in ingredients_lower:
            return False
    
    return True

def analyze_if_palm_oil_free(ingredients):
    """Analyze if product is palm oil free"""
    if not ingredients:
        return None
    
    palm_oil_keywords = ['palm oil', 'palm kernel', 'palmitate']
    ingredients_lower = ingredients.lower()
    
    for keyword in palm_oil_keywords:
        if keyword in ingredients_lower:
            return False
    
    return True

def clean_text(text):
    """Clean text for display"""
    if not text:
        return ''
    return text.strip()
