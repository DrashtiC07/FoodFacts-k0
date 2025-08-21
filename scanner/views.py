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
from .ml_utils import eco_predictor, nova_analyzer
from .additives_analyzer import analyze_additives  # Import additives analyzer
from django.utils import timezone

# Configure logging
logger = logging.getLogger(__name__)

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = getattr(settings, 'TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')

def index(request):
    """Scanner home page with recent products"""
    recent_products = Product.objects.all().order_by('-created_at')[:6]
    return render(request, 'scanner/index.html', {'recent_products': recent_products})

def product_detail(request, barcode):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f" Attempting to load product with barcode: {barcode}")
        product = get_object_or_404(Product, barcode=barcode)
        logger.info(f" Product found: {product.name}")
        
        # Record scan history only for authenticated users
        if request.user.is_authenticated:
            ScanHistory.objects.get_or_create(user=request.user, product=product)
        
        # Calculate health score if missing
        if product.health_score is None and product.nutrition_info:
            try:
                product.health_score = product.calculate_health_score()
                product.save()
                logger.info(f" Health score calculated: {product.health_score}")
            except Exception as health_error:
                logger.warning(f" Health score calculation failed: {str(health_error)}")
        
        # Get nutrition facts with better error handling
        nutrition_facts = []
        try:
            nutrition_fact_obj = NutritionFact.objects.filter(product=product).first()
            if nutrition_fact_obj:
                nutrition_facts = nutrition_fact_obj
                logger.info(" Nutrition facts loaded from database")
            elif product.nutrition_info:
                nutrition_facts = parse_nutrition_facts(product.nutrition_info)
                logger.info(" Nutrition facts parsed from product info")
        except Exception as nf_error:
            logger.warning(f" Nutrition facts error for product {barcode}: {str(nf_error)}")
            nutrition_facts = []
        
        # Get NOVA group info with error handling
        nova_info = None
        try:
            if product.nova_group:
                nova_info = get_nova_group_info(product.nova_group)
                logger.info(f" NOVA info loaded for group {product.nova_group}")
        except Exception as nova_error:
            logger.warning(f" NOVA info error for product {barcode}: {str(nova_error)}")
        
        # Get additives analysis with error handling
        additives_analysis = None
        try:
            if product.ingredients:
                from .additives_analyzer import analyze_additives
                additives_analysis = analyze_additives(product.ingredients)
                logger.info(f" Additives analysis completed: {additives_analysis.get('total_additives', 0)} additives found")
        except Exception as additives_error:
            logger.warning(f" Additives analysis error for product {barcode}: {str(additives_error)}")
        
        # Get environmental impact with error handling
        environmental_impact = None
        try:
            environmental_impact = calculate_environmental_impact(product)
            logger.info(" Environmental impact calculated")
        except Exception as env_error:
            logger.warning(f" Environmental impact error for product {barcode}: {str(env_error)}")
        
        # Get reviews
        reviews = ProductReview.objects.filter(product=product).select_related('user').order_by('-created_at')[:10]
        logger.info(f" Loaded {reviews.count()} reviews")
        
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
        
        # Check if product is favorite and get existing review (only for authenticated users)
        existing_review = None
        is_favorite = False
        if request.user.is_authenticated:
            existing_review = ProductReview.objects.filter(user=request.user, product=product).first()
            is_favorite = FavoriteProduct.objects.filter(user=request.user, product=product).exists()

        logger.info(" Successfully prepared all product data, rendering template")
        
        return render(request, 'scanner/product.html', {
            'product': product,
            'nutrition_facts': nutrition_facts,
            'dietary_flags': dietary_flags,
            'existing_review': existing_review,
            'user_review': existing_review,  # Added user_review alias for template compatibility
            'is_favorite': is_favorite,
            'nova_info': nova_info,
            'additives_analysis': additives_analysis,
            'environmental_impact': environmental_impact,
            'reviews': reviews,
        })
        
    except Product.DoesNotExist:
        logger.error(f" Product with barcode {barcode} not found in database")
        messages.error(request, f'Product with barcode {barcode} not found.')
        return redirect('scanner:search')
    except Exception as e:
        logger.error(f" Unexpected error in product_detail for barcode {barcode}: {str(e)}")
        logger.error(f" Error type: {type(e).__name__}")
        import traceback
        logger.error(f" Traceback: {traceback.format_exc()}")
        messages.error(request, f'An error occurred while loading product details: {str(e)}. Please try again.')
        return redirect('scanner:search')

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
    """Enhanced manual barcode entry with better validation and API calls"""
    if request.method == 'POST':
        barcode = request.POST.get('barcode', '').strip()
        
        if not barcode:
            messages.error(request, 'Please enter a barcode.')
            return render(request, 'scanner/search.html', {'barcode_error': barcode})
        
        if not barcode.isdigit() or len(barcode) < 8 or len(barcode) > 14:
            messages.error(request, 'Please enter a valid barcode (8-14 digits).')
            return render(request, 'scanner/search.html', {'barcode_error': barcode})
        
        try:
            # First check if product exists in database
            product = Product.objects.get(barcode=barcode)
            
            # Add to scan history if user is authenticated
            if request.user.is_authenticated:
                ScanHistory.objects.get_or_create(
                    user=request.user,
                    product=product,
                    defaults={'scanned_at': timezone.now()}
                )
            
            # Redirect to product detail page
            return redirect('scanner:product_detail', barcode=barcode)
            
        except Product.DoesNotExist:
            try:
                import requests
                
                # Try OpenFoodFacts API
                response = requests.get(f'https://world.openfoodfacts.org/api/v0/product/{barcode}.json', timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('status') == 1 and 'product' in data:
                        product_data = data['product']
                        
                        # Create new product from API data
                        product = Product.objects.create(
                            barcode=barcode,
                            name=product_data.get('product_name', f'Product {barcode}'),
                            brand=product_data.get('brands', ''),
                            category=product_data.get('categories', ''),
                            ingredients=product_data.get('ingredients_text', ''),
                            image_url=product_data.get('image_url', ''),
                            nutrition_info=product_data.get('nutriments', {}),
                            ecoscore=product_data.get('ecoscore_grade', '').upper(),
                            health_score=calculate_health_score(product_data.get('nutriments', {}))
                        )
                        
                        # Add to scan history if user is authenticated
                        if request.user.is_authenticated:
                            ScanHistory.objects.get_or_create(
                                user=request.user,
                                product=product,
                                defaults={'scanned_at': timezone.now()}
                            )
                        
                        messages.success(request, f'Product found and added to database!')
                        return redirect('scanner:product_detail', barcode=barcode)
                
                # If not found in OpenFoodFacts, show error with suggestions
                suggest_urls = [
                    f'https://world.openfoodfacts.org/product/{barcode}',
                    f'https://www.barcodelookup.com/{barcode}',
                ]
                
                return render(request, 'scanner/search.html', {
                    'barcode_not_found': barcode,
                    'suggest_urls': suggest_urls
                })
                
            except Exception as e:
                messages.error(request, 'An error occurred while searching for the product. Please try again.')
                return render(request, 'scanner/search.html', {'barcode_error': barcode})
    
    return redirect('scanner:search')

@login_required
def submit_review(request, barcode):
    """Handle product review submission with enhanced error handling"""
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
        
        try:
            review, created = ProductReview.objects.update_or_create(
                user=request.user,
                product=product,
                defaults={
                    'rating': rating,
                    'review_text': review_text
                }
            )
            
            if created:
                messages.success(request, 'Thank you for your review!')
            else:
                messages.success(request, 'Your review has been updated!')
                
            logger.info(f" Review saved successfully for user {request.user.username} on product {barcode}")
            
        except Exception as e:
            logger.error(f" Error saving review: {str(e)}")
            messages.error(request, 'Failed to save your review. Please try again.')
    
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
    """Enhanced search products across name, brand and barcode"""
    query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'name')
    products = []
    
    if query:
        search_filter = (
            Q(name__icontains=query) | 
            Q(brand__icontains=query) |
            Q(barcode__icontains=query) |
            Q(category__icontains=query) |
            Q(ingredients__icontains=query)
        )
        
        products = Product.objects.filter(search_filter)
        
        # Apply sorting
        if sort_by == 'name':
            products = products.order_by('name')
        elif sort_by == 'brand':
            products = products.order_by('brand', 'name')
        elif sort_by == 'recent':
            products = products.order_by('-created_at')
        else:
            products = products.order_by('name')
        
        # Pagination
        paginator = Paginator(products, 20)  # Show 20 products per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        if not products.exists():
            messages.info(request, f'No products found for "{query}"')
    else:
        page_obj = None
    
    return render(request, 'scanner/search.html', {
        'page_obj': page_obj,
        'query': query,
        'results_count': paginator.count if query and products.exists() else 0,
        'sort_by': sort_by,
    })

@login_required
def save_product(request):
    """Enhanced save product functionality with comprehensive error handling"""
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        try:
            logger.info(f" Save product request from user: {request.user.username}")
            data = json.loads(request.body)
            barcode = data.get('barcode')
            
            if not barcode:
                logger.error(" Save product failed: No barcode provided")
                return JsonResponse({'success': False, 'error': 'Barcode is required'})
            
            logger.info(f" Processing product with barcode: {barcode}")
            
            # Get or create the product
            product, created = Product.objects.get_or_create(
                barcode=barcode,
                defaults={
                    'name': data.get('name', 'Unknown Product'),
                    'brand': data.get('brand', ''),
                    'category': data.get('category', ''),
                    'ingredients': data.get('ingredients', ''),
                    'image_url': data.get('image_url', ''),
                }
            )
            
            logger.info(f" Product {'created' if created else 'found'}: {product.name}")
            
            # Update product information if provided
            if not created:
                updated_fields = []
                for field in ['name', 'brand', 'category', 'ingredients', 'image_url']:
                    if data.get(field):
                        setattr(product, field, data[field])
                        updated_fields.append(field)
                
                # Update nutrition info if provided
                if data.get('nutrition_info'):
                    product.nutrition_info = data['nutrition_info']
                    updated_fields.append('nutrition_info')
                
                if updated_fields:
                    product.save()
                    logger.info(f" Updated product fields: {updated_fields}")
            
            # Create scan history entry for the current user only
            scan_history, scan_created = ScanHistory.objects.get_or_create(
                user=request.user,  # Ensure it's tied to current user
                product=product,
                defaults={'scanned_at': timezone.now()}
            )
            
            # If scan already exists, update the timestamp
            if not scan_created:
                scan_history.scanned_at = timezone.now()
                scan_history.save()
                logger.info(f" Updated existing scan history for user {request.user.username}")
            else:
                logger.info(f" Created new scan history for user {request.user.username}")
            
            # Calculate health score if nutrition info is available
            try:
                if product.nutrition_info:
                    health_score = product.calculate_health_score()
                    if health_score is not None:
                        product.health_score = health_score
                        product.save()
                        logger.info(f" Health score calculated: {health_score}")
            except Exception as health_error:
                logger.warning(f" Health score calculation failed: {str(health_error)}")
            
            # Save nutrition facts to database if provided
            try:
                if data.get('nutrition_facts'):
                    nutrition_fact, nf_created = NutritionFact.objects.get_or_create(
                        product=product,
                        defaults=data['nutrition_facts']
                    )
                    if not nf_created:
                        # Update existing nutrition facts
                        for key, value in data['nutrition_facts'].items():
                            setattr(nutrition_fact, key, value)
                        nutrition_fact.save()
                    logger.info(f" Nutrition facts {'created' if nf_created else 'updated'}")
            except Exception as nf_error:
                logger.warning(f" Nutrition facts save failed: {str(nf_error)}")
            
            return JsonResponse({
                'success': True,
                'message': 'Product saved successfully!',
                'product_id': product.id,
                'created': created,
                'scan_recorded': True
            })
            
        except json.JSONDecodeError:
            logger.error(" Save product failed: Invalid JSON data")
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            logger.error(f" Save product error: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

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
    """Save product to database with enhanced fields and ML predictions"""
    try:
        ingredients = product_info.get('ingredients', '')
        
        ecoscore = product_info.get('ecoscore', '')
        if not ecoscore:
            # Use ML to predict eco-score
            ecoscore = eco_predictor.predict_ecoscore({
                'ingredients': ingredients,
                'nutrition_info': product_info.get('nutrition', {}),
                'nova_group': product_info.get('nova_group'),
                'category': product_info.get('category', '')
            })
        
        nova_group = product_info.get('nova_group')
        if not nova_group:
            nova_group = nova_analyzer.predict_nova_group(ingredients, product_info.get('category', ''))
        
        product = Product.objects.create(
            barcode=barcode,
            name=product_info['name'][:255],  # Ensure name fits in field
            brand=product_info.get('brand', '')[:255],
            category=product_info.get('category', '')[:255],
            ingredients=ingredients,
            nutrition_info=product_info.get('nutrition', {}),
            image_url=product_info.get('image_url', '')[:500],  # Ensure URL fits
            ecoscore=ecoscore[:1] if ecoscore else '',  # Ensure single character
            nova_group=nova_group,
            vegan=analyze_if_vegan(ingredients),
            vegetarian=analyze_if_vegetarian(ingredients),
            palm_oil_free=analyze_if_palm_oil_free(ingredients),
        )
        
        # Calculate health score
        product.health_score = product.calculate_health_score()
        product.save()
        
        nutrition_data = product_info.get('nutrition', {})
        if nutrition_data:
            try:
                # Extract nutrition values with proper key mapping
                nutrition_fields = {
                    'energy_kcal': nutrition_data.get('energy-kcal_100g') or nutrition_data.get('energy-kcal') or nutrition_data.get('energy_kcal'),
                    'fat': nutrition_data.get('fat_100g') or nutrition_data.get('fat'),
                    'saturated_fat': nutrition_data.get('saturated-fat_100g') or nutrition_data.get('saturated_fat'),
                    'carbohydrates': nutrition_data.get('carbohydrates_100g') or nutrition_data.get('carbohydrates'),
                    'sugars': nutrition_data.get('sugars_100g') or nutrition_data.get('sugars'),
                    'proteins': nutrition_data.get('proteins_100g') or nutrition_data.get('proteins'),
                    'salt': nutrition_data.get('salt_100g') or nutrition_data.get('salt'),
                    'fiber': nutrition_data.get('fiber_100g') or nutrition_data.get('fiber'),
                }
                
                # Clean and validate nutrition values
                cleaned_nutrition = {}
                for key, value in nutrition_fields.items():
                    if value is not None:
                        try:
                            # Convert to float and validate
                            float_value = float(value)
                            if 0 <= float_value <= 1000:  # Reasonable range for nutrition values
                                cleaned_nutrition[key] = float_value
                        except (ValueError, TypeError):
                            logger.warning(f" Invalid nutrition value for {key}: {value}")
                            continue
                
                # Only create nutrition facts if we have valid data
                if cleaned_nutrition:
                    nutrition_fact, created = NutritionFact.objects.update_or_create(
                        product=product,
                        defaults=cleaned_nutrition
                    )
                    logger.info(f" Nutrition facts {'created' if created else 'updated'} for product {barcode}")
                else:
                    logger.warning(f" No valid nutrition data found for product {barcode}")
                    
            except Exception as nutrition_error:
                logger.error(f" Error saving nutrition facts for product {barcode}: {str(nutrition_error)}")
                # Don't fail the entire product save if nutrition facts fail
        
        logger.info(f" Product {barcode} saved successfully with health score {product.health_score}")
        return product
        
    except Exception as e:
        logger.error(f" Error saving product {barcode}: {str(e)}")
        raise

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

def get_nova_group_info(nova_group):
    """Get detailed NOVA group information"""
    nova_groups = {
        1: {
            'name': 'Unprocessed or minimally processed foods',
            'description': 'Natural foods obtained directly from plants or animals and do not undergo any alteration following their removal from nature.',
            'health_impact': 'These foods are the basis of nutritionally balanced, delicious, culturally appropriate diets.',
            'recommendation': 'Make these foods the basis of your diet.',
            'icon': 'check-circle'
        },
        2: {
            'name': 'Processed culinary ingredients',
            'description': 'Substances derived from Group 1 foods or from nature by processes such as pressing, grinding, crushing, pulverizing, and refining.',
            'health_impact': 'Used in small amounts to season and cook Group 1 foods and to make varied and enjoyable culinary preparations.',
            'recommendation': 'Use in small amounts for cooking and seasoning.',
            'icon': 'droplet'
        },
        3: {
            'name': 'Processed foods',
            'description': 'Products made by adding salt, oil, sugar or other Group 2 substances to Group 1 foods.',
            'health_impact': 'Most processed foods have two or three ingredients, and are recognizable as modified versions of Group 1 foods.',
            'recommendation': 'Consume in moderation as part of meals based on Group 1 foods.',
            'icon': 'exclamation-triangle'
        },
        4: {
            'name': 'Ultra-processed foods',
            'description': 'Industrial formulations made entirely or mostly from substances extracted from foods, derived from food constituents, or synthesized in laboratories.',
            'health_impact': 'Typically energy-dense, high in unhealthy types of fat, refined starches, free sugars and salt, and poor sources of protein, dietary fiber and micronutrients.',
            'recommendation': 'Avoid or consume very occasionally as treats.',
            'icon': 'x-circle'
        }
    }
    
    try:
        group_num = int(nova_group)
        return nova_groups.get(group_num, None)
    except (ValueError, TypeError):
        return None

def calculate_environmental_impact(product):
    """Calculate environmental impact based on product data"""
    if not product.ingredients:
        return None
    
    # Simple environmental impact calculation
    ingredients_lower = product.ingredients.lower()
    
    # High impact ingredients
    high_impact_ingredients = [
        'palm oil', 'beef', 'lamb', 'cheese', 'butter', 'cream',
        'cocoa', 'chocolate', 'coffee', 'almonds', 'avocado'
    ]
    
    # Medium impact ingredients
    medium_impact_ingredients = [
        'chicken', 'pork', 'fish', 'eggs', 'milk', 'rice',
        'wheat', 'sugar', 'soy', 'corn'
    ]
    
    # Low impact ingredients
    low_impact_ingredients = [
        'vegetables', 'fruits', 'beans', 'lentils', 'peas',
        'oats', 'barley', 'quinoa', 'herbs', 'spices'
    ]
    
    high_impact_count = sum(1 for ingredient in high_impact_ingredients if ingredient in ingredients_lower)
    medium_impact_count = sum(1 for ingredient in medium_impact_ingredients if ingredient in ingredients_lower)
    low_impact_count = sum(1 for ingredient in low_impact_ingredients if ingredient in ingredients_lower)
    
    # Calculate scores
    ingredient_score = max(0, 100 - (high_impact_count * 30) - (medium_impact_count * 15))
    
    # Processing impact based on NOVA group
    processing_score = {
        1: 90,  # Minimal processing
        2: 75,  # Processed ingredients
        3: 60,  # Processed foods
        4: 30   # Ultra-processed
    }.get(product.nova_group or 4, 50)
    
    # Overall score
    overall_score = (ingredient_score + processing_score) // 2
    
    # Determine grade
    if overall_score >= 80:
        grade = 'A'
    elif overall_score >= 65:
        grade = 'B'
    elif overall_score >= 50:
        grade = 'C'
    elif overall_score >= 35:
        grade = 'D'
    else:
        grade = 'E'
    
    # Carbon footprint estimate
    if overall_score >= 75:
        carbon_footprint = 'Very Low'
    elif overall_score >= 60:
        carbon_footprint = 'Low'
    elif overall_score >= 45:
        carbon_footprint = 'Moderate'
    elif overall_score >= 30:
        carbon_footprint = 'High'
    else:
        carbon_footprint = 'Very High'
    
    recommendations = []
    if high_impact_count > 0:
        recommendations.append("Look for products with fewer high-impact ingredients")
    if product.nova_group and product.nova_group >= 3:
        recommendations.append("Choose less processed alternatives when possible")
    if 'palm oil' in ingredients_lower:
        recommendations.append("Consider palm oil-free alternatives")
    
    return {
        'overall_score': overall_score,
        'grade': grade,
        'carbon_footprint_estimate': carbon_footprint,
        'ingredient_impact': {
            'score': ingredient_score,
            'high_impact_count': high_impact_count,
            'medium_impact_count': medium_impact_count,
            'low_impact_count': low_impact_count
        },
        'processing_impact': {
            'score': processing_score,
            'description': f"NOVA Group {product.nova_group or 'Unknown'} processing level"
        },
        'recommendations': recommendations
    }

def calculate_health_score(nutriments):
    """Calculate a simple health score based on nutrition data"""
    try:
        score = 50  # Base score
        
        # Positive factors
        if nutriments.get('fiber_100g', 0) > 3:
            score += 10
        if nutriments.get('proteins_100g', 0) > 10:
            score += 10
        
        # Negative factors
        if nutriments.get('saturated-fat_100g', 0) > 5:
            score -= 15
        if nutriments.get('sugars_100g', 0) > 15:
            score -= 15
        if nutriments.get('sodium_100g', 0) > 1:
            score -= 10
        
        return max(0, min(100, score))
    except:
        return 50

@login_required
def scan_history(request):
    """Display user's scan history with proper user filtering and pagination"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f" Loading scan history for user: {request.user.username} (ID: {request.user.id})")
    
    scans = ScanHistory.objects.filter(
        user=request.user  # This ensures only current user's scans
    ).select_related('product').order_by('-scanned_at')
    
    logger.info(f" Scan history for user {request.user.username}: {scans.count()} scans found")
    
    # Debug: Log first few scan entries
    for i, scan in enumerate(scans[:3]):
        logger.info(f" Scan {i+1}: {scan.product.name} by user {scan.user.username} at {scan.scanned_at}")
    
    paginator = Paginator(scans, 20)  # Show 20 scans per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'scanner/history.html', {
        'page_obj': page_obj,
        'total_scans': scans.count(),
        'user_scans_only': True,  # Flag to indicate user-specific filtering
        'current_user': request.user.username  # For debugging in template
    })

@login_required
def suggest_nova_group(request):
    """Auto-detect NOVA group based on ingredients analysis"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            barcode = data.get('barcode')
            
            if not barcode:
                return JsonResponse({'success': False, 'error': 'Barcode is required'})
            
            product = get_object_or_404(Product, barcode=barcode)
            
            if not product.ingredients:
                return JsonResponse({'success': False, 'error': 'No ingredients available for analysis'})
            
            nova_group = auto_detect_nova_group(product.ingredients)
            nova_info = get_nova_group_info(nova_group)
            
            # Update product with suggested NOVA group
            product.nova_group = nova_group
            product.save()
            
            return JsonResponse({
                'success': True,
                'nova_group': nova_group,
                'description': nova_info['name'] if nova_info else f'NOVA Group {nova_group}',
                'recommendation': nova_info['recommendation'] if nova_info else 'Processing level updated'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'})
        except Exception as e:
            logger.error(f"NOVA group suggestion error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Analysis failed'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

def auto_detect_nova_group(ingredients_text):
    """
    Auto-detect NOVA group based on ingredients analysis
    NOVA 1: Unprocessed or minimally processed foods
    NOVA 2: Processed culinary ingredients  
    NOVA 3: Processed foods
    NOVA 4: Ultra-processed foods
    """
    if not ingredients_text:
        return 4  # Default to ultra-processed if no ingredients
    
    ingredients_lower = ingredients_text.lower()
    
    # Count industrial additives (E-numbers and chemical names)
    industrial_additives = [
        'e1', 'e2', 'e3', 'e4', 'e5', 'e6', 'e7', 'e8', 'e9',  # E-numbers
        'sodium benzoate', 'potassium sorbate', 'calcium propionate',
        'monosodium glutamate', 'msg', 'high fructose corn syrup',
        'artificial flavor', 'artificial colour', 'artificial color',
        'modified starch', 'hydrolyzed protein', 'maltodextrin',
        'carrageenan', 'xanthan gum', 'guar gum', 'lecithin',
        'tartrazine', 'sunset yellow', 'brilliant blue', 'allura red'
    ]
    
    additive_count = sum(1 for additive in industrial_additives if additive in ingredients_lower)
    
    # Check for whole food indicators
    whole_foods = [
        'almonds', 'cashews', 'peanuts', 'walnuts', 'rice', 'wheat', 'oats',
        'tomatoes', 'onions', 'garlic', 'ginger', 'turmeric', 'cumin',
        'milk', 'cream', 'butter', 'cheese', 'yogurt', 'eggs',
        'chicken', 'beef', 'fish', 'lentils', 'chickpeas', 'beans'
    ]
    
    whole_food_count = sum(1 for food in whole_foods if food in ingredients_lower)
    
    # Check for processing indicators
    processing_terms = [
        'concentrate', 'isolate', 'extract', 'powder', 'syrup',
        'modified', 'hydrolyzed', 'refined', 'enriched', 'fortified'
    ]
    
    processing_count = sum(1 for term in processing_terms if term in ingredients_lower)
    
    # NOVA classification logic
    if additive_count >= 5:
        return 4  # Ultra-processed: >5 industrial additives
    elif whole_food_count >= 3 and additive_count == 0:
        return 1  # Minimally processed: mostly whole foods, no additives
    elif processing_count >= 2 or additive_count >= 2:
        return 4  # Ultra-processed: significant processing or additives
    elif 'canned' in ingredients_lower or 'preserved' in ingredients_lower:
        return 3  # Processed: canned or preserved foods
    elif whole_food_count >= 1 and additive_count <= 1:
        return 2  # Processed culinary ingredients
    else:
        return 3  # Default to processed for ambiguous cases

@login_required
def edit_review(request, review_id):
    """Edit an existing product review"""
    from accounts.models import ProductReview
    
    # Get the review and ensure it belongs to the current user
    review = get_object_or_404(ProductReview, id=review_id, user=request.user)
    product = review.product
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text', '').strip()
        
        if not rating:
            messages.error(request, 'Please select a rating')
            return render(request, 'scanner/edit_review.html', {
                'review': review,
                'product': product
            })
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            messages.error(request, 'Invalid rating value')
            return render(request, 'scanner/edit_review.html', {
                'review': review,
                'product': product
            })
        
        try:
            # Update the review
            review.rating = rating
            review.review_text = review_text
            review.save()
            
            messages.success(request, 'Your review has been updated successfully!')
            logger.info(f"Review updated successfully for user {request.user.username} on product {product.barcode}")
            
            # Redirect to dashboard after successful update
            return redirect('accounts:dashboard')
            
        except Exception as e:
            logger.error(f"Error updating review: {str(e)}")
            messages.error(request, 'Failed to update your review. Please try again.')
    
    # GET request - show the edit form
    return render(request, 'scanner/edit_review.html', {
        'review': review,
        'product': product
    })

@login_required
@require_http_methods(["POST"])
def delete_review(request, review_id):
    """Delete an existing product review"""
    from accounts.models import ProductReview
    
    try:
        # Get the review and ensure it belongs to the current user
        review = get_object_or_404(ProductReview, id=review_id, user=request.user)
        product_name = review.product.name
        
        # Delete the review
        review.delete()
        
        logger.info(f"Review deleted successfully for user {request.user.username} on product {product_name}")
        
        return JsonResponse({
            'success': True,
            'message': f'Your review for {product_name} has been deleted successfully!'
        })
        
    except ProductReview.DoesNotExist:
        logger.warning(f"Delete review failed: Review {review_id} not found for user {request.user.username}")
        return JsonResponse({
            'success': False,
            'error': 'Review not found or you do not have permission to delete it.'
        }, status=404)
        
    except Exception as e:
        logger.error(f"Error deleting review {review_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to delete review. Please try again.'
        }, status=500)
