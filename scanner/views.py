import cv2
import numpy as np
import requests
import pytesseract
import re
import os
import logging
import io
import json
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from pyzbar.pyzbar import decode
from scanner.models import Product, ScanHistory, NutritionFact
from accounts.models import FavoriteProduct, ProductReview

# Configure logging
logger = logging.getLogger(__name__)

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = getattr(settings, 'TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')

def index(request):
    """Scanner home page with recent products"""
    recent_products = Product.objects.all().order_by('-created_at')[:6]
    return render(request, 'scanner/index.html', {'recent_products': recent_products})

@login_required
def product_detail(request, barcode):
    try:
        product = get_object_or_404(Product, barcode=barcode)
        
        # Record scan history if not already exists
        if request.user.is_authenticated:
            ScanHistory.objects.get_or_create(user=request.user, product=product)
        
        # Calculate health score if missing
        if product.health_score is None and product.nutrition_info:
            product.health_score = product.calculate_health_score()
            product.save()
        
        # Get nutrition facts (using NutritionFact model if available)
        try:
            nutrition_facts = NutritionFact.objects.filter(product=product).first()
            if not nutrition_facts:
                nutrition_facts = parse_nutrition_facts(product.nutrition_info) if product.nutrition_info else []
        except:
            nutrition_facts = parse_nutrition_facts(product.nutrition_info) if product.nutrition_info else []
        
        dietary_flags = [
            {
                'type': 'vegan', 'status': product.vegan,
                'label': 'Vegan' if product.vegan else 'Not Vegan',
                'color': 'success' if product.vegan else 'danger',
                'icon': '✅' if product.vegan else '❌'
            },
            {
                'type': 'vegetarian', 'status': product.vegetarian,
                'label': 'Vegetarian' if product.vegetarian else 'Not Vegetarian',
                'color': 'success' if product.vegetarian else 'danger',
                'icon': '✅' if product.vegetarian else '❌'
            },
            {
                'type': 'palm_oil', 'status': product.palm_oil_free,
                'label': 'Palm Oil Free' if product.palm_oil_free else 'Contains Palm Oil',
                'color': 'success' if product.palm_oil_free else 'danger',
                'icon': '✅' if product.palm_oil_free else '⚠️'
            }
        ]
        
        # Check if product is favorite and get existing review
        existing_review = None
        is_favorite = False
        if request.user.is_authenticated:
            existing_review = ProductReview.objects.filter(user=request.user, product=product).first()
            is_favorite = FavoriteProduct.objects.filter(user=request.user, product=product).exists()

        return render(request, 'scanner/product.html', {
            'product': product,
            'nutrition_facts': nutrition_facts,
            'dietary_flags': dietary_flags,
            'existing_review': existing_review,
            'is_favorite': is_favorite,
        })
        
    except Exception as e:
        logger.error(f"Product detail error: {str(e)}")
        messages.error(request, 'Error loading product details.')
        return redirect('scanner:index')

@login_required
def scan_barcode(request):
    if request.method == 'POST' and request.FILES.get('image'):
        try:
            image_file = request.FILES['image']
            img = process_uploaded_image(image_file)
            
            if img is None:
                messages.error(request, 'Invalid image format')
                return render(request, 'scanner/scan.html', {
                    'error': 'Invalid image format',
                    'allow_manual': True
                })
            
            barcode_result = detect_barcode_enhanced(img)
            
            if not barcode_result:
                messages.warning(request, 'No barcode detected')
                return render(request, 'scanner/scan.html', {
                    'error': 'No barcode detected',
                    'allow_manual': True,
                    'tips': [
                        'Ensure good lighting',
                        'Keep the barcode flat',
                        'Try different angles',
                        'Clean the camera lens'
                    ]
                })
            
            barcode = barcode_result['code']
            barcode_type = barcode_result['type']
            
            # Check local database first
            product = Product.objects.filter(barcode=barcode).first()
            if product:
                if request.user.is_authenticated:
                    ScanHistory.objects.get_or_create(user=request.user, product=product)
                messages.info(request, f'Found: {product.name}')
                return redirect('scanner:product_detail', barcode=barcode)
            
            # Try external APIs
            product_info = fetch_product_info_enhanced(barcode, barcode_type)
            
            if product_info:
                product = save_product(barcode, product_info, barcode_type)
                if request.user.is_authenticated:
                    ScanHistory.objects.create(user=request.user, product=product)
                messages.success(request, f'Added: {product.name}')
                return redirect('scanner:product_detail', barcode=barcode)
            else:
                messages.error(request, 'Product not found')
                return render(request, 'scanner/scan.html', {
                    'barcode': barcode,
                    'suggest_urls': [
                        f'https://world.openfoodfacts.org/product/{barcode}',
                        f'https://in.openfoodfacts.org/product/{barcode}'
                    ],
                    'allow_manual': True
                })
                
        except Exception as e:
            logger.error(f"Scan error: {str(e)}")
            messages.error(request, 'Scanning error occurred')
            return render(request, 'scanner/scan.html', {
                'error': 'Scan failed',
                'allow_manual': True
            })
    
    return render(request, 'scanner/scan.html')

@login_required
def manual_entry(request):
    if request.method == 'POST':
        barcode = request.POST.get('barcode', '').strip()
        
        # Enhanced validation
        if not barcode.isdigit():
            messages.error(request, 'Barcode must contain only numbers')
            return render(request, 'scanner/scan.html', {'allow_manual': True})
        
        if not (8 <= len(barcode) <= 14):
            messages.error(request, 'Barcode must be 8-14 digits long')
            return render(request, 'scanner/scan.html', {'allow_manual': True})
        
        # Validate barcode format
        barcode_result = validate_barcode_enhanced(barcode)
        if not barcode_result:
            messages.error(request, 'Invalid barcode format or checksum')
            return render(request, 'scanner/scan.html', {
                'allow_manual': True,
                'barcode': barcode
            })
        
        validated_barcode = barcode_result['code']
        barcode_type = barcode_result['type']
        
        product = Product.objects.filter(barcode=validated_barcode).first()
        if product:
            if request.user.is_authenticated:
                ScanHistory.objects.get_or_create(user=request.user, product=product)
            return redirect('scanner:product_detail', barcode=validated_barcode)
        
        product_info = fetch_product_info_enhanced(validated_barcode, barcode_type)
        if product_info:
            product = save_product(validated_barcode, product_info, barcode_type)
            if request.user.is_authenticated:
                ScanHistory.objects.create(user=request.user, product=product)
            messages.success(request, f'Added: {product.name}')
            return redirect('scanner:product_detail', barcode=validated_barcode)
        else:
            messages.error(request, 'Product not found')
            return render(request, 'scanner/scan.html', {
                'barcode': validated_barcode,
                'suggest_urls': [
                    f'https://world.openfoodfacts.org/product/{validated_barcode}',
                    f'https://in.openfoodfacts.org/product/{validated_barcode}'
                ],
                'allow_manual': True
            })
    
    return redirect('scanner:scan')

@login_required
def submit_review(request, barcode):
    """Handle product review submission"""
    if request.method == 'POST':
        product = get_object_or_404(Product, barcode=barcode)
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text', '').strip()
        
        if not rating:
            messages.error(request, 'Please select a rating')
            return redirect('scanner:product_detail', barcode=barcode)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid rating value')
            return redirect('scanner:product_detail', barcode=barcode)
        
        # Update or create review
        ProductReview.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={
                'rating': rating,
                'review_text': review_text
            }
        )
        
        # Update product rating stats
        product.update_rating_stats()
        messages.success(request, 'Thank you for your review!')
    
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
            messages.info(request, f'Removed {product.name} from favorites')
        else:
            messages.success(request, f'Added {product.name} to favorites')
    
    return redirect('scanner:product_detail', barcode=barcode)

def search_products(request):
    """Search products across name, brand and barcode"""
    query = request.GET.get('q', '').strip()
    products = []
    
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(brand__icontains=query) |
            Q(barcode__icontains=query) |
            Q(category__icontains=query)
        ).order_by('name')
        
        # Pagination
        paginator = Paginator(products, 20)  # Show 20 products per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        if not products.exists():
            messages.info(request, f'No products found for "{query}"')
    
    return render(request, 'scanner/search.html', {
        'page_obj': page_obj if query else None,
        'query': query,
        'results_count': paginator.count if query else 0
    })

@login_required
def scan_history(request):
    """Display user's scan history with pagination"""
    scans = ScanHistory.objects.filter(
        user=request.user
    ).select_related('product').order_by('-scanned_at')
    
    paginator = Paginator(scans, 10)  # Show 10 scans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'scanner/history.html', {
        'page_obj': page_obj,
        'total_scans': scans.count()
    })

# Helper Functions
def process_uploaded_image(image_file):
    """Process uploaded image for barcode detection with enhanced handling"""
    try:
        image_data = image_file.read()
        img_array = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is None or img.size == 0:
            return None
        
        # Auto-rotate based on EXIF
        try:
            pil_img = Image.open(io.BytesIO(image_data))
            if hasattr(pil_img, '_getexif') and pil_img._getexif():
                exif = pil_img._getexif()
                orientation = exif.get(0x0112, 1)
                
                rotation_map = {
                    3: cv2.ROTATE_180,
                    6: cv2.ROTATE_90_COUNTERCLOCKWISE,
                    8: cv2.ROTATE_90_CLOCKWISE
                }
                
                if orientation in rotation_map:
                    img = cv2.rotate(img, rotation_map[orientation])
        except Exception as e:
            logger.warning(f"EXIF processing failed: {e}")
        
        return resize_to_optimal(img)
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return None

def resize_to_optimal(img, target_width=1000):
    """Resize image for optimal OCR performance"""
    height, width = img.shape[:2]
    if width > target_width:
        ratio = target_width / width
        new_height = int(height * ratio)
        return cv2.resize(img, (target_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    return img

def detect_barcode_enhanced(img):
    """Enhanced barcode detection with multiple methods"""
    # First try pyzbar
    try:
        barcodes = decode(img)
        if barcodes:
            return {
                'code': barcodes[0].data.decode('utf-8'),
                'type': barcodes[0].type
            }
    except Exception as e:
        logger.error(f"Pyzbar detection error: {str(e)}")
    
    # Fallback to OCR methods if pyzbar fails
    methods = [
        detect_with_preprocessing,
        detect_with_zoning_enhanced,
        detect_with_adaptive_threshold_enhanced,
        detect_with_contours_enhanced
    ]
    
    for method in methods:
        try:
            result = method(img)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Barcode detection method {method.__name__} failed: {e}")
            continue
    
    return None

def detect_with_preprocessing(img):
    """Detect barcode with image preprocessing"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Multiple preprocessing approaches
    preprocessed_images = []
    
    # 1. Basic preprocessing
    denoised = cv2.fastNlMeansDenoising(gray)
    preprocessed_images.append(denoised)
    
    # 2. Contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(gray)
    preprocessed_images.append(enhanced)
    
    # 3. Gaussian blur + threshold
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocessed_images.append(thresh)
    
    # OCR configurations
    configs = [
        '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
        '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789',
        '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'
    ]
    
    for processed_img in preprocessed_images:
        for config in configs:
            try:
                data = pytesseract.image_to_string(processed_img, config=config)
                numbers = re.sub(r'[^\d]', '', data)
                
                if numbers:
                    result = validate_barcode_enhanced(numbers)
                    if result:
                        return result
            except Exception:
                continue
                
    return None

def detect_with_zoning_enhanced(img):
    """Enhanced zoning with overlapping regions"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    
    # Create overlapping zones
    zones = []
    zone_height = height // 4
    for i in range(5):  # 5 overlapping horizontal zones
        start_y = max(0, i * zone_height - zone_height // 4)
        end_y = min(height, start_y + zone_height + zone_height // 2)
        zones.append(gray[start_y:end_y, 0:width])
    
    # OCR configurations
    configs = [
        '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
        '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
    ]
    
    for zone in zones:
        if zone.size == 0:
            continue
            
        for config in configs:
            try:
                data = pytesseract.image_to_string(zone, config=config)
                numbers = re.sub(r'[^\d]', '', data)
                
                if numbers:
                    result = validate_barcode_enhanced(numbers)
                    if result:
                        return result
            except Exception:
                continue
                
    return None

def detect_with_adaptive_threshold_enhanced(img):
    """Enhanced adaptive thresholding"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Multiple adaptive threshold methods
    methods = [
        (cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 11, 7),
        (cv2.ADAPTIVE_THRESH_MEAN_C, 15, 10)
    ]
    
    for method, block_size, c in methods:
        try:
            thresh = cv2.adaptiveThreshold(gray, 255, method, cv2.THRESH_BINARY, block_size, c)
            
            # Apply morphological operations
            kernel = np.ones((2,2), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            processed = cv2.medianBlur(processed, 3)
            
            configs = [
                '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
                '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
            ]
            
            for config in configs:
                try:
                    data = pytesseract.image_to_string(processed, config=config)
                    numbers = re.sub(r'[^\d]', '', data)
                    
                    if numbers:
                        result = validate_barcode_enhanced(numbers)
                        if result:
                            return result
                except Exception:
                    continue
                    
        except Exception:
            continue
            
    return None

def detect_with_contours_enhanced(img):
    """Enhanced contour-based detection"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Filter for barcode-like rectangles
        if w > 80 and h > 20 and (w/h) > 1.5:
            # Add padding
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img.shape[1] - x, w + 2 * padding)
            h = min(img.shape[0] - y, h + 2 * padding)
            
            roi = img[y:y+h, x:x+w]
            
            if roi.size == 0:
                continue
            
            configs = [
                '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
                '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
            ]
            
            for config in configs:
                try:
                    data = pytesseract.image_to_string(roi, config=config)
                    numbers = re.sub(r'[^\d]', '', data)
                    
                    if numbers:
                        result = validate_barcode_enhanced(numbers)
                        if result:
                            return result
                except Exception:
                    continue
                    
    return None

def validate_barcode_enhanced(barcode_string):
    """Enhanced barcode validation supporting multiple formats"""
    if not barcode_string or not barcode_string.isdigit():
        return None
    
    # Try different lengths and formats
    possible_codes = []
    
    for length in [13, 12, 8, 14]:  # EAN-13, UPC-A, EAN-8, ITF-14
        if len(barcode_string) >= length:
            # Try from beginning
            code = barcode_string[:length]
            possible_codes.append((code, length))
            
            # Try from end
            if len(barcode_string) > length:
                code = barcode_string[-length:]
                possible_codes.append((code, length))
    
    # Also try the full string if reasonable
    if 8 <= len(barcode_string) <= 14:
        possible_codes.append((barcode_string, len(barcode_string)))
    
    # Validate each possible code
    for code, length in possible_codes:
        barcode_type = get_barcode_type(code, length)
        if barcode_type and validate_checksum(code, barcode_type):
            return {
                'code': code,
                'type': barcode_type,
                'length': length
            }
    
    return None

def get_barcode_type(code, length):
    """Determine barcode type based on code and length"""
    if length == 13:
        return 'EAN-13'
    elif length == 12:
        return 'UPC-A'
    elif length == 8:
        return 'EAN-8'
    elif length == 14:
        return 'ITF-14'
    elif length <= 14:
        return 'Generic'
    return None

def validate_checksum(code, barcode_type):
    """Validate barcode checksum based on type"""
    try:
        if barcode_type in ['EAN-13', 'UPC-A']:
            return validate_ean13_checksum(code)
        elif barcode_type == 'EAN-8':
            return validate_ean8_checksum(code)
        elif barcode_type == 'ITF-14':
            return validate_itf14_checksum(code)
        else:
            # For generic codes, just check if it's reasonable
            return len(code) >= 8 and code.isdigit()
    except Exception:
        return False

def validate_ean13_checksum(code):
    """Validate EAN-13 checksum"""
    if len(code) != 13:
        return False
    
    try:
        checksum = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(code[:12]))
        return (10 - (checksum % 10)) % 10 == int(code[12])
    except (ValueError, IndexError):
        return False

def validate_ean8_checksum(code):
    """Validate EAN-8 checksum"""
    if len(code) != 8:
        return False
    
    try:
        checksum = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(code[:7]))
        return (10 - (checksum % 10)) % 10 == int(code[7])
    except (ValueError, IndexError):
        return False

def validate_itf14_checksum(code):
    """Validate ITF-14 checksum"""
    if len(code) != 14:
        return False
    
    try:
        checksum = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(code[:13]))
        return (10 - (checksum % 10)) % 10 == int(code[13])
    except (ValueError, IndexError):
        return False

def fetch_product_info_enhanced(barcode, source):
    """Fetch product info with multiple API fallbacks"""
    cache_key = f"product_{barcode}"
    if cached := cache.get(cache_key):
        return cached

    apis_to_try = [
        lambda: try_openfoodfacts(barcode, 'india'),
        lambda: try_openfoodfacts(barcode, 'global'),
        lambda: try_barcodelookup(barcode),
        lambda: try_upcitemdb(barcode)
    ]

    for api in apis_to_try:
        try:
            product_info = api()
            if product_info:
                cache.set(cache_key, product_info, timeout=86400)  # Cache for 24 hours
                return product_info
        except Exception as e:
            logger.warning(f"API {api.__name__} failed: {str(e)}")

    return None

def try_openfoodfacts(barcode, region='global'):
    """Try Open Food Facts API"""
    url = settings.API_CONFIG['openfoodfacts'][region].format(barcode=barcode)
    headers = {'User-Agent': 'FoodScanner/2.0 (Enhanced Barcode Support)'}
    response = requests.get(url, headers=headers, timeout=5)
    response.raise_for_status()
    data = response.json()
    
    if data.get('status') == 1:
        product = data.get('product', {})
        return {
            'name': clean_text(product.get('product_name_in') or product.get('product_name') or f'Product {barcode}'),
            'brand': clean_text(product.get('brands', '')),
            'category': clean_text(product.get('categories', '')),
            'ingredients': clean_text(product.get('ingredients_text_in') or product.get('ingredients_text', '')),
            'nutrition': product.get('nutriments', {}),
            'image_url': product.get('image_url', ''),
            'ecoscore': product.get('ecoscore_grade', '').upper(),
            'nova_group': product.get('nova_group', ''),
            'fssai': product.get('fssai_license_no', ''),
            'source': f'openfoodfacts-{region}'
        }
    return None

def try_barcodelookup(barcode):
    """Try BarcodeLookup API"""
    if not settings.API_CONFIG['barcodelookup']['key']:
        return None
        
    params = {
        'barcode': barcode,
        'key': settings.API_CONFIG['barcodelookup']['key']
    }
    headers = {'User-Agent': 'FoodScanner/2.0'}
    response = requests.get(settings.API_CONFIG['barcodelookup']['url'], params=params, headers=headers, timeout=5)
    response.raise_for_status()
    data = response.json()
    
    if data.get('products'):
        product = data['products'][0]
        return {
            'name': clean_text(product.get('product_name') or product.get('title') or f'Product {barcode}'),
            'brand': clean_text(product.get('brand', '')),
            'category': clean_text(product.get('category', '')),
            'ingredients': clean_text(product.get('ingredients', '')),
            'nutrition': parse_barcodelookup_nutrition(product),
            'image_url': product.get('images', [''])[0],
            'source': 'barcodelookup'
        }
    return None

def try_upcitemdb(barcode):
    """Try UPCitemDB API"""
    params = {'upc': barcode}
    headers = {'User-Agent': 'FoodScanner/2.0'}
    if settings.API_CONFIG['upcitemdb']['key']:
        headers['Authorization'] = f"Bearer {settings.API_CONFIG['upcitemdb']['key']}"
    
    response = requests.get(settings.API_CONFIG['upcitemdb']['url'], params=params, headers=headers, timeout=5)
    response.raise_for_status()
    data = response.json()
    
    if data.get('items'):
        item = data['items'][0]
        return {
            'name': clean_text(item.get('title', f'Product {barcode}')),
            'brand': clean_text(item.get('brand', '')),
            'category': clean_text(item.get('category', '')),
            'ingredients': '',
            'nutrition': {},
            'image_url': item.get('images', [''])[0],
            'source': 'upcitemdb'
        }
    return None

def parse_barcodelookup_nutrition(product):
    """Parse BarcodeLookup nutrition data"""
    nutrition = {}
    if product.get('nutrition_facts'):
        for fact in product['nutrition_facts']:
            name = fact.get('name', '').lower()
            value = fact.get('value')
            if value:
                nutrition[name] = float(value.split()[0])  # Extract numeric value
    return nutrition

def save_product(barcode, product_info, source):
    """Save product to database with enhanced fields"""
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
        nova_group=product_info.get('nova_group', ''),
        fssai=product_info.get('fssai', ''),
        vegan=analyze_if_vegan(ingredients),
        vegetarian=analyze_if_vegetarian(ingredients),
        palm_oil_free=analyze_if_palm_oil_free(ingredients),
        source=source
    )
    
    # Calculate health score
    product.health_score = product.calculate_health_score()
    product.save()
    
    # Save nutrition facts to separate model if available
    if product_info.get('nutrition'):
        try:
            NutritionFact.objects.update_or_create(
                product=product,
                defaults={
                    'energy_kcal': product_info['nutrition'].get('energy-kcal_100g'),
                    'fat': product_info['nutrition'].get('fat_100g'),
                    'saturated_fat': product_info['nutrition'].get('saturated-fat_100g'),
                    'carbohydrates': product_info['nutrition'].get('carbohydrates_100g'),
                    'sugars': product_info['nutrition'].get('sugars_100g'),
                    'proteins': product_info['nutrition'].get('proteins_100g'),
                    'salt': product_info['nutrition'].get('salt_100g'),
                    'fiber': product_info['nutrition'].get('fiber_100g'),
                }
            )
        except Exception as e:
            logger.error(f"Error saving nutrition facts: {e}")
    
    return product

def parse_nutrition_facts(nutrition_info):
    """Parse nutrition information"""
    if not nutrition_info:
        return []
    
    facts = []
    mapping = {
        'energy-kcal': {'name': 'Energy', 'unit': 'kcal'},
        'fat': {'name': 'Fat', 'unit': 'g'},
        'saturated-fat': {'name': 'Saturated Fat', 'unit': 'g'},
        'carbohydrates': {'name': 'Carbs', 'unit': 'g'},
        'sugars': {'name': 'Sugars', 'unit': 'g'},
        'proteins': {'name': 'Protein', 'unit': 'g'},
        'salt': {'name': 'Salt', 'unit': 'g'},
        'fiber': {'name': 'Fiber', 'unit': 'g'},
    }
    
    for key, info in mapping.items():
        if key in nutrition_info:
            value = nutrition_info[key]
            if isinstance(value, (int, float)):
                facts.append({
                    'name': info['name'],
                    'value': round(value, 1),
                    'unit': info['unit']
                })
    return facts

def analyze_if_vegan(ingredients):
    """Enhanced vegan analysis with comprehensive checks"""
    if not ingredients:
        return None
    
    non_vegan_keywords = [
        'milk', 'cheese', 'yogurt', 'butter', 'cream', 'whey', 'casein',
        'egg', 'albumin', 'gelatin', 'honey', 'beeswax', 'carmine',
        'shellac', 'vitamin d3', 'cholecalciferol', 'fish oil'
    ]
    
    vegan_exceptions = [
        'coconut milk', 'almond milk', 'soy milk', 'oat milk',
        'vegan cheese', 'plant-based'
    ]
    
    ingredients_lower = ingredients.lower()
    
    # Remove vegan exceptions first
    for exception in vegan_exceptions:
        ingredients_lower = ingredients_lower.replace(exception, '')
    
    # Check for non-vegan ingredients
    return not any(keyword in ingredients_lower for keyword in non_vegan_keywords)

def analyze_if_vegetarian(ingredients):
    """Enhanced vegetarian analysis"""
    if not ingredients:
        return None
    
    non_vegetarian_keywords = [
        'meat', 'beef', 'pork', 'chicken', 'fish', 'tuna', 'salmon',
        'shrimp', 'prawn', 'gelatin', 'rennet', 'carmine'
    ]
    
    vegetarian_exceptions = [
        'vegetable rennet', 'microbial rennet', 'plant-based'
    ]
    
    ingredients_lower = ingredients.lower()
    
    # Remove vegetarian exceptions first
    for exception in vegetarian_exceptions:
        ingredients_lower = ingredients_lower.replace(exception, '')
    
    # Check for non-vegetarian ingredients
    return not any(keyword in ingredients_lower for keyword in non_vegetarian_keywords)

def analyze_if_palm_oil_free(ingredients):
    """Enhanced palm oil analysis"""
    if not ingredients:
        return None
    
    palm_oil_keywords = [
        'palm oil', 'palm kernel oil', 'palmitate', 'sodium palmitate',
        'palm stearin', 'elaeis guineensis'
    ]
    
    palm_free_exceptions = [
        'palm oil free', 'no palm oil', 'without palm oil'
    ]
    
    ingredients_lower = ingredients.lower()
    
    # Remove palm-free exceptions first
    for exception in palm_free_exceptions:
        ingredients_lower = ingredients_lower.replace(exception, '')
    
    # Check for palm oil ingredients
    return not any(keyword in ingredients_lower for keyword in palm_oil_keywords)

def clean_text(text):
    """Clean text for display"""
    if not text:
        return ''
    
    text = str(text).strip()
    text = ' '.join(text.split())  # Remove extra whitespace
    
    # Remove language prefixes
    prefixes_to_remove = ['en:', 'fr:', 'de:', 'es:']
    for prefix in prefixes_to_remove:
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    
    return text