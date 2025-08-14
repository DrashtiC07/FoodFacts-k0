import cv2
import numpy as np
import requests
import pytesseract
import re
from PIL import Image
import io
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages # For user feedback
from scanner.models import Product, NutritionFact, ScanHistory, Review # Import ScanHistory and NutritionFact
from accounts.models import CustomUser, FavoriteProduct, DietaryGoal # Import CustomUser, FavoriteProduct, and DietaryGoal
import logging
from pyzbar.pyzbar import decode
from django.views.decorators.http import require_http_methods
from django.db.models import Q

# Configure logging
logger = logging.getLogger(__name__)

# Configure Tesseract (update path as needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def fetch_product_data(barcode):
    url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 1:
            product_data = data.get('product', {})
            return product_data
    return None

def parse_nutrition_facts(product_data):
    nutrition_data = product_data.get('nutriments', {})
    return {
        'energy_kcal': nutrition_data.get('energy-kcal_100g'),
        'fat': nutrition_data.get('fat_100g'),
        'saturated_fat': nutrition_data.get('saturated-fat_100g'),
        'carbohydrates': nutrition_data.get('carbohydrates_100g'),
        'sugars': nutrition_data.get('sugars_100g'),
        'proteins': nutrition_data.get('proteins_100g'),
        'salt': nutrition_data.get('salt_100g'),
        'fiber': nutrition_data.get('fiber_100g'),
    }

def index(request):
    """Home page view"""
    recent_products = Product.objects.all().order_by('-created_at')[:6]
    context = {
        'recent_products': recent_products,
    }
    return render(request, 'scanner/index.html', context)

def scan(request):
    if request.method == 'POST':
        barcode = request.POST.get('barcode')
        if barcode:
            product_data = fetch_product_data(barcode)
            if product_data:
                product, created = Product.objects.get_or_create(
                    barcode=barcode,
                    defaults={
                        'name': product_data.get('product_name', 'Unknown Product'),
                        'brand': product_data.get('brands', 'Unknown Brand'),
                        'category': product_data.get('categories', 'Unknown Category'),
                        'image_url': product_data.get('image_front_url') or product_data.get('image_url'),
                        'ingredients': product_data.get('ingredients_text_en', product_data.get('ingredients_text')),
                        'ecoscore': product_data.get('ecoscore_grade', '').upper(),
                        'nova_group': product_data.get('nova_group'),
                    }
                )

                # Update product fields if it already exists but some fields were missing
                if not created:
                    updated = False
                    if not product.name and product_data.get('product_name'):
                        product.name = product_data['product_name']
                        updated = True
                    if not product.brand and product_data.get('brands'):
                        product.brand = product_data['brands']
                        updated = True
                    if not product.category and product_data.get('categories'):
                        product.category = product_data['categories']
                        updated = True
                    if not product.image_url and (product_data.get('image_front_url') or product_data.get('image_url')):
                        product.image_url = product_data.get('image_front_url') or product_data.get('image_url')
                        updated = True
                    if not product.ingredients and (product_data.get('ingredients_text_en') or product_data.get('ingredients_text')):
                        product.ingredients = product_data.get('ingredients_text_en', product_data.get('ingredients_text'))
                        updated = True
                    if updated:
                        product.save()

                # Create or update NutritionFact
                nutrition_facts_data = parse_nutrition_facts(product_data)
                nutrition_fact, created_nf = NutritionFact.objects.update_or_create(
                    product=product,
                    defaults=nutrition_facts_data
                )

                # Record scan history
                if request.user.is_authenticated:
                    ScanHistory.objects.create(user=request.user, product=product)

                return redirect('scanner:product_detail', barcode=barcode)
            else:
                return render(request, 'scanner/scan.html', {'error': 'Product not found or API error.'})
    return render(request, 'scanner/scan.html')

@require_http_methods(["GET", "POST"])
def product_detail(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)
    nutrition_facts = NutritionFact.objects.filter(product=product).first()
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    
    is_favorite = False
    user_review = None
    if request.user.is_authenticated:
        is_favorite = FavoriteProduct.objects.filter(user=request.user, product=product).exists()
        ScanHistory.objects.get_or_create(user=request.user, product=product) # Record scan history on detail view
        try:
            user_review = Review.objects.get(user=request.user, product=product)
        except Review.DoesNotExist:
            pass

    context = {
        'product': product,
        'nutrition_facts': nutrition_facts,
        'reviews': reviews,
        'is_favorite': is_favorite,
        'user_review': user_review,
    }
    return render(request, 'scanner/product_detail.html', context)

@login_required
def submit_review(request, barcode):
    if request.method == 'POST':
        product = get_object_or_404(Product, barcode=barcode)
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')

        if rating and review_text:
            Review.objects.update_or_create(
                user=request.user,
                product=product,
                defaults={'rating': rating, 'review_text': review_text}
            )
            messages.success(request, 'Your review has been submitted!')
            return redirect('scanner:product_detail', barcode=barcode)
    return redirect('scanner:product_detail', barcode=barcode) # Redirect back if not POST or invalid data

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
                # Record scan history even if product exists
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
            # Record scan history for newly saved product
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

def process_uploaded_image(image_file):
    """Enhanced image processing with better error handling"""
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

def detect_with_pyzbar(img):
    """Detect barcodes using pyzbar library."""
    try:
        # pyzbar can work with color images, but grayscale might be slightly faster
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        barcodes = decode(gray)
        
        if barcodes:
            # Prioritize the first detected barcode
            barcode_data = barcodes[0].data.decode('utf-8')
            barcode_type = barcodes[0].type
            
            # pyzbar already performs checksum validation for common types
            return {
                'code': barcode_data,
                'type': barcode_type,
                'length': len(barcode_data)
            }
    except Exception as e:
        logger.error(f"Pyzbar detection failed: {e}")
    return None

def detect_barcode_enhanced(img):
    """Enhanced barcode detection supporting multiple formats, prioritizing pyzbar."""
    
    # 1. Try pyzbar first (generally more accurate and faster for actual barcodes)
    pyzbar_result = detect_with_pyzbar(img)
    if pyzbar_result:
        return pyzbar_result
        
    # 2. If pyzbar fails, fall back to pytesseract-based OCR methods
    methods = [
        detect_with_preprocessing,
        detect_with_zoning_enhanced,
        detect_with_adaptive_threshold_enhanced,
        detect_with_contours_enhanced,
        detect_with_morphology,
        detect_with_edge_detection
    ]
    
    for method in methods:
        try:
            # These methods internally call validate_barcode_enhanced on their OCR output
            result = method(img) 
            if result:
                logger.info(f"Barcode detected using {method.__name__} (OCR fallback): {result}")
                return result
        except Exception as e:
            logger.warning(f"OCR fallback method {method.__name__} failed: {e}")
            continue
    
    return None

def detect_with_preprocessing(img):
    """Enhanced preprocessing for better OCR"""
    try:
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
        
        # 4. Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        preprocessed_images.append(morph)
        
        # OCR configurations for different barcode types
        configs = [
            '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
            '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789',
            '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789',
            '--psm 13 --oem 3 -c tessedit_char_whitelist=0123456789'
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
                    
    except Exception as e:
        logger.error(f"Preprocessing detection failed: {e}")
    
    return None

def detect_with_zoning_enhanced(img):
    """Enhanced zoning with overlapping regions"""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # Create overlapping zones for better coverage
        zones = []
        
        # Horizontal zones
        zone_height = height // 4
        for i in range(5):  # 5 overlapping horizontal zones
            start_y = max(0, i * zone_height - zone_height // 4)
            end_y = min(height, start_y + zone_height + zone_height // 2)
            zones.append(gray[start_y:end_y, 0:width])
        
        # Vertical zones
        zone_width = width // 4
        for i in range(5):  # 5 overlapping vertical zones
            start_x = max(0, i * zone_width - zone_width // 4)
            end_x = min(width, start_x + zone_width + zone_width // 2)
            zones.append(gray[0:height, start_x:end_x])
        
        # Center zone
        center_y, center_x = height // 2, width // 2
        zone_h, zone_w = height // 3, width // 3
        zones.append(gray[center_y-zone_h//2:center_y+zone_h//2, 
                         center_x-zone_w//2:center_x+zone_w//2])
        
        configs = [
            '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
            '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789',
            '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'
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
                    
    except Exception as e:
        logger.error(f"Enhanced zoning detection failed: {e}")
    
    return None

def detect_with_adaptive_threshold_enhanced(img):
    """Enhanced adaptive thresholding"""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Multiple adaptive threshold methods
        methods = [
            (cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 11, 7),
            (cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 15, 10),
            (cv2.ADAPTIVE_THRESH_MEAN_C, 11, 7),
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
                
    except Exception as e:
        logger.error(f"Enhanced adaptive threshold detection failed: {e}")
    
    return None

def detect_with_contours_enhanced(img):
    """Enhanced contour-based detection"""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Multiple edge detection methods
        edge_methods = [
            lambda x: cv2.Canny(x, 50, 150),
            lambda x: cv2.Canny(x, 30, 100),
            lambda x: cv2.Canny(x, 100, 200)
        ]
        
        for edge_method in edge_methods:
            try:
                edges = edge_method(gray)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
                
                for cnt in contours:
                    x, y, w, h = cv2.boundingRect(cnt)
                    
                    # Enhanced filtering for barcode-like rectangles
                    aspect_ratio = w / h if h > 0 else 0
                    area = cv2.contourArea(cnt)
                    
                    if (w > 80 and h > 20 and aspect_ratio > 1.5 and area > 1000):
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
                            '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789',
                            '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'
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
                                
            except Exception:
                continue
                
    except Exception as e:
        logger.error(f"Enhanced contour detection failed: {e}")
    
    return None

def detect_with_morphology(img):
    """Morphological operations for barcode detection"""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Create rectangular kernel for barcode detection
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
        
        # Apply morphological operations
        morph = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        
        # Threshold
        _, thresh = cv2.threshold(morph, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            if w > 100 and h > 30:
                roi = img[y:y+h, x:x+w]
                
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
                        
    except Exception as e:
        logger.error(f"Morphological detection failed: {e}")
    
    return None

def detect_with_edge_detection(img):
    """Edge detection based barcode finding"""
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Sobel edge detection
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Combine edges
        edges = np.sqrt(sobelx**2 + sobely**2)
        edges = np.uint8(edges / edges.max() * 255)
        
        # Threshold
        _, thresh = cv2.threshold(edges, 50, 255, cv2.THRESH_BINARY)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            if w > 80 and h > 25 and w/h > 2:
                roi = img[y:y+h, x:x+w]
                
                configs = [
                    '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
                    '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789'
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
                        
    except Exception as e:
        logger.error(f"Edge detection failed: {e}")
    
    return None

def validate_barcode_enhanced(barcode_string):
    """Enhanced barcode validation supporting multiple formats"""
    if not barcode_string or not barcode_string.isdigit():
        return None
    
    # Try different lengths and formats
    possible_codes = []
    
    # Extract potential barcodes of different lengths
    for length in [13, 12, 8, 14]:  # EAN-13, UPC-A, EAN-8, ITF-14
        if len(barcode_string) >= length:
            # Try from beginning
            code = barcode_string[:length]
            possible_codes.append((code, length))
            
            # Try from end (in case there are leading digits)
            if len(barcode_string) > length:
                code = barcode_string[-length:]
                possible_codes.append((code, length))
    
    # Also try the full string if it's a reasonable length
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

def fetch_product_info_enhanced(barcode, barcode_type):
    """Enhanced product info fetching with better error handling"""
    apis = [
        ('OpenFoodFacts', fetch_openfoodfacts),
        ('BarcodeLookup', fetch_barcodelookup),
        ('UPCDatabase', fetch_upcdatabase)
    ]
    
    for api_name, api_func in apis:
        try:
            logger.info(f"Trying {api_name} for {barcode_type} barcode: {barcode}")
            product_info = api_func(barcode)
            if product_info:
                product_info['detected_type'] = barcode_type
                logger.info(f"Successfully fetched from {api_name}")
                return product_info
        except Exception as e:
            logger.warning(f"{api_name} failed for barcode {barcode}: {e}")
            continue
    
    return None

def fetch_openfoodfacts(barcode):
    """Enhanced OpenFoodFacts API call"""
    try:
        url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
        headers = {
            'User-Agent': 'FoodScanner/2.0 (Enhanced Barcode Support)',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, timeout=5, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if data.get('status') == 1:
            product = data.get('product', {})
            return {
                'name': clean_text(product.get('product_name', f'Product {barcode}')),
                'brand': clean_text(product.get('brands', '')),
                'category': clean_text(product.get('categories', '')),
                'ingredients': clean_text(product.get('ingredients_text', '')),
                'nutrition': product.get('nutriments', {}),
                'image_url': product.get('image_url', ''),
                'ecoscore': product.get('ecoscore_grade', '').upper(),
                'nova_group': product.get('nova_group'),
                'allergens': product.get('allergens_tags', []),
                'labels': product.get('labels_tags', []),
                'source': 'openfoodfacts'
            }
    except Exception as e:
        logger.error(f"OpenFoodFacts API error: {e}")
    
    return None

def fetch_barcodelookup(barcode):
    """Enhanced BarcodeLookup API call"""
    try:
        # Note: You'll need to get an API key from barcodelookup.com
        api_key = getattr(settings, 'BARCODE_LOOKUP_API_KEY', None)
        if not api_key:
            logger.warning("BarcodeLookup API key not configured")
            return None
        
        url = f"https://api.barcodelookup.com/v3/products"
        params = {
            'barcode': barcode,
            'formatted': 'y',
            'key': api_key
        }
        headers = {'Accept': 'application/json'}
        
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data.get('products'):
            product = data['products'][0]
            return {
                'name': clean_text(product.get('product_name', f'Product {barcode}')),
                'brand': clean_text(product.get('brand', '')),
                'category': clean_text(product.get('category', '')),
                'description': clean_text(product.get('description', '')),
                'image_url': product.get('images', [None])[0],
                'source': 'barcodelookup'
            }
    except Exception as e:
        logger.error(f"BarcodeLookup API error: {e}")
    
    return None

def fetch_upcdatabase(barcode):
    """UPC Database API call"""
    try:
        url = f"https://api.upcdatabase.org/product/{barcode}"
        headers = {
            'User-Agent': 'FoodScanner/2.0',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        if data.get('success'):
            return {
                'name': clean_text(data.get('title', f'Product {barcode}')),
                'brand': clean_text(data.get('brand', '')),
                'category': clean_text(data.get('category', '')),
                'description': clean_text(data.get('description', '')),
                'source': 'upcdatabase'
            }
    except Exception as e:
        logger.error(f"UPCDatabase API error: {e}")
    
    return None

def save_product(barcode, product_info, barcode_type):
    """Enhanced product saving with barcode type"""
    ingredients = product_info.get('ingredients', '')
    
    # Create product instance
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
    
    # Calculate health score
    product.health_score = product.calculate_health_score()
    
    # Detect allergens
    product.allergens = product.detect_allergens()
    
    # Save the complete product
    product.save()
    logger.info(f"Saved {barcode_type} product: {barcode}")
    
    return product

def manual_entry(request):
    """Enhanced manual entry with better validation"""
    if request.method == 'POST':
        barcode = request.POST.get('barcode', '').strip()
        
        # Enhanced barcode validation
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
        
        # Validate barcode format
        barcode_result = validate_barcode_enhanced(barcode)
        if not barcode_result:
            return render(request, 'scanner/scan.html', {
                'error': 'Invalid barcode format or checksum.',
                'allow_manual': True,
                'barcode': barcode
            })
        
        validated_barcode = barcode_result['code']
        barcode_type = barcode_result['type']
        
        try:
            # Check if product already exists
            product = Product.objects.get(barcode=validated_barcode)
            return redirect('scanner:product_detail', barcode=validated_barcode)
        except Product.DoesNotExist:
            pass
        
        # Fetch product info
        product_info = fetch_product_info_enhanced(validated_barcode, barcode_type)
        
        if product_info:
            product = save_product(validated_barcode, product_info, barcode_type)
            return redirect('scanner:product_detail', barcode=validated_barcode)
        else:
            return render(request, 'scanner/scan.html', {
                'error': 'Product not found in any database.',
                'barcode': validated_barcode,
                'barcode_type': barcode_type,
                'suggest_url': f'https://world.openfoodfacts.org/product/{validated_barcode}',
                'allow_manual': True
            })
    
    return redirect('scanner:scan')

def analyze_if_vegan(ingredients):
    """Enhanced vegan analysis"""
    if not ingredients:
        return None  # Unknown instead of False
    
    # More comprehensive non-vegan ingredients list
    non_vegan_keywords = [
        # Dairy
        'milk', 'cheese', 'yogurt', 'yoghurt', 'butter', 'cream', 'ghee',
        'whey', 'casein', 'lactose', 'lactitol', 'lactalbumin',
        # Eggs
        'egg', 'eggs', 'albumin', 'ovalbumin', 'ovomucin', 'lysozyme',
        # Meat & Fish
        'gelatin', 'gelatine', 'collagen', 'isinglass', 'fish oil',
        'omega-3 from fish', 'anchovy', 'tuna', 'salmon',
        # Insects & Animal derivatives
        'honey', 'beeswax', 'royal jelly', 'propolis', 'carmine', 'cochineal',
        'shellac', 'confectioner\'s glaze', 'lanolin', 'tallow', 'lard',
        # Vitamins from animal sources
        'vitamin d3', 'cholecalciferol', 'vitamin b12 from animal',
        # Other
        'pepsin', 'rennet', 'chitin', 'chitosan'
    ]
    
    # Vegan-friendly alternatives
    vegan_exceptions = [
        'coconut milk', 'almond milk', 'soy milk', 'oat milk', 'rice milk',
        'cashew milk', 'hemp milk', 'pea milk',
        'vegan cheese', 'plant-based butter', 'nutritional yeast',
        'agar agar', 'carrageenan', 'guar gum', 'xanthan gum',
        'soy lecithin', 'sunflower lecithin', 'plant-based omega-3',
        'algae oil', 'flax oil', 'chia oil'
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
    
    # Non-vegetarian ingredients (meat, fish, but allows dairy and eggs)
    non_vegetarian_keywords = [
        # Meat and poultry
        'meat', 'beef', 'pork', 'lamb', 'chicken', 'turkey', 'duck',
        'bacon', 'ham', 'sausage', 'pepperoni', 'salami', 'prosciutto',
        # Fish and seafood
        'fish', 'tuna', 'salmon', 'cod', 'sardine', 'anchovy', 'mackerel',
        'shrimp', 'prawn', 'crab', 'lobster', 'oyster', 'mussel', 'clam',
        'squid', 'octopus', 'fish oil', 'fish sauce', 'fish extract',
        # Animal-derived ingredients that require slaughter
        'gelatin', 'gelatine', 'rennet', 'pepsin', 'carmine', 'cochineal',
        'isinglass', 'lard', 'tallow'
    ]
    
    # Vegetarian-friendly alternatives
    vegetarian_exceptions = [
        'vegetable rennet', 'microbial rennet', 'plant-based',
        'imitation crab', 'mock fish', 'vegan fish', 'algae oil'
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
    
    # Comprehensive palm oil derivatives list
    palm_oil_keywords = [
        'palm oil', 'palm kernel oil', 'palm fruit oil', 'palmitate',
        'sodium palmitate', 'palmitic acid', 'palm stearin', 'palmolein',
        'sodium lauryl sulfate', 'sodium laureth sulfate', 'sls', 'sles',
        'glyceryl stearate', 'stearic acid', 'stearyl alcohol',
        'cetyl palmitate', 'octyl palmitate', 'palmityl alcohol',
        'elaeis guineensis', 'hydrogenated palm glycerides',
        'sodium palm kernelate', 'palm alcohol', 'palmitoyl'
    ]
    
    # Palm-free alternatives
    palm_free_exceptions = [
        'olive oil', 'coconut oil', 'sunflower oil', 'canola oil',
        'soybean oil', 'corn oil', 'avocado oil', 'peanut oil',
        'sesame oil', 'grape seed oil', 'almond oil', 'safflower oil'
    ]
    
    ingredients_lower = ingredients.lower()
    
    # Remove palm-free exceptions first
    for exception in palm_free_exceptions:
        ingredients_lower = ingredients_lower.replace(exception, '')
    
    # Check for palm oil ingredients
    return not any(keyword in ingredients_lower for keyword in palm_oil_keywords)

def clean_text(text):
    """Enhanced text cleaning"""
    if not text:
        return ""
    
    # Convert to string and clean
    text = str(text).strip()
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common prefixes/suffixes
    prefixes_to_remove = ['en:', 'fr:', 'de:', 'es:']
    for prefix in prefixes_to_remove:
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    
    return text

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
    return render(request, 'scanner/scan_history.html', context)
