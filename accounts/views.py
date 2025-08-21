from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .forms import CustomUserCreationForm, LoginForm
from .models import CustomUser, ProductReview, FavoriteProduct, DietaryGoal, WeeklyNutritionLog, PersonalizedTip, TrackedItem
from scanner.models import Product, ScanHistory

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Food Scanner.')
            return redirect('scanner:index')
        else:
            messages.error(request, 'Registration failed. Please correct the errors.')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/login_register.html', {'form': form, 'register': True})

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                next_url = request.GET.get('next', 'scanner:index')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login_register.html', {'form': form, 'register': False})

@login_required
def user_logout(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('scanner:index')

@login_required
def dashboard(request):
    user = request.user

    # Fetch scan history (last 10 scans)
    scan_history = ScanHistory.objects.filter(user=user).select_related('product').order_by('-scanned_at')[:10]
    print(f"[DEBUG] Dashboard - User: {user.username}, Scan history count: {scan_history.count()}")

    # Fetch favorite products
    favorite_products = FavoriteProduct.objects.filter(
        user=user, 
        product__barcode__isnull=False,
        product__barcode__gt=''
    ).select_related('product')[:10]
    print(f"[DEBUG] Dashboard - Favorite products count: {favorite_products.count()}")

    tracked_items = TrackedItem.objects.filter(user=user).select_related('product')[:10]

    # Fetch user's reviews
    user_reviews = ProductReview.objects.filter(user=user).select_related('product').order_by('-created_at')[:5]

    # Get or create dietary goals
    dietary_goals, created = DietaryGoal.objects.get_or_create(
        user=user,
        defaults={
            'calories_target': 2000,
            'protein_target': 50,
            'fat_target': 70,
            'carbs_target': 300,
            'sugar_target': 50,
            'sodium_target': 2300,
        }
    )

    today = timezone.now().date()
    if dietary_goals.last_reset_date < today:
        dietary_goals.calories_consumed = 0
        dietary_goals.protein_consumed = 0
        dietary_goals.fat_consumed = 0
        dietary_goals.carbs_consumed = 0
        dietary_goals.sugar_consumed = 0
        dietary_goals.sodium_consumed = 0
        dietary_goals.last_reset_date = today
        dietary_goals.save()

    # Calculate progress percentages
    calories_progress = (dietary_goals.calories_consumed / dietary_goals.calories_target * 100) if dietary_goals.calories_target > 0 else 0
    protein_progress = (dietary_goals.protein_consumed / dietary_goals.protein_target * 100) if dietary_goals.protein_target > 0 else 0
    fat_progress = (dietary_goals.fat_consumed / dietary_goals.fat_target * 100) if dietary_goals.fat_target > 0 else 0
    carbs_progress = (dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100) if dietary_goals.carbs_target > 0 else 0
    sugar_progress = (dietary_goals.sugar_consumed / dietary_goals.sugar_target * 100) if dietary_goals.sugar_target > 0 else 0
    sodium_progress = (dietary_goals.sodium_consumed / dietary_goals.sodium_target * 100) if dietary_goals.sodium_target > 0 else 0

    # Calculate remaining amounts
    calories_remaining = max(0, dietary_goals.calories_target - dietary_goals.calories_consumed)
    protein_remaining = max(0, dietary_goals.protein_target - dietary_goals.protein_consumed)
    fat_remaining = max(0, dietary_goals.fat_target - dietary_goals.fat_consumed)
    carbs_remaining = max(0, dietary_goals.carbs_target - dietary_goals.carbs_consumed)
    sugar_remaining = max(0, dietary_goals.sugar_target - dietary_goals.sugar_consumed)
    sodium_remaining = max(0, dietary_goals.sodium_target - dietary_goals.sodium_consumed)

    week_ago = today - timedelta(days=7)
    weekly_logs = WeeklyNutritionLog.objects.filter(
        user=user, 
        week_start_date__gte=week_ago
    ).order_by('-week_start_date')[:4]

    # Calculate recent activity stats
    recent_scans_count = ScanHistory.objects.filter(user=user, scanned_at__gte=timezone.now() - timedelta(days=7)).count()
    
    # Calculate days active
    days_active = (timezone.now().date() - user.date_joined.date()).days

    personalized_tips = get_or_create_persistent_tips(
        user, dietary_goals, calories_progress, protein_progress, fat_progress, 
        carbs_progress, sugar_progress, sodium_progress, recent_scans_count, days_active
    )

    context = {
        'user': user,
        'scan_history': scan_history,
        'favorite_products': favorite_products,
        'tracked_items': tracked_items,
        'user_reviews': user_reviews,
        'dietary_goals': dietary_goals,
        'calories_progress': min(calories_progress, 100),
        'protein_progress': min(protein_progress, 100),
        'fat_progress': min(fat_progress, 100),
        'carbs_progress': min(carbs_progress, 100),
        'sugar_progress': min(sugar_progress, 100),
        'sodium_progress': min(sodium_progress, 100),
        'calories_remaining': calories_remaining,
        'protein_remaining': protein_remaining,
        'fat_remaining': fat_remaining,
        'carbs_remaining': carbs_remaining,
        'sugar_remaining': sugar_remaining,
        'sodium_remaining': sodium_remaining,
        'recent_scans_count': recent_scans_count,
        'days_active': days_active,
        'weekly_logs': weekly_logs,
        'personalized_tips': personalized_tips,
    }
    return render(request, 'accounts/dashboard.html', context)

def get_or_create_persistent_tips(user, dietary_goals, calories_progress, protein_progress, fat_progress, 
                                carbs_progress, sugar_progress, sodium_progress, recent_scans_count, days_active):
    """Get existing persistent tips or create new ones based on current nutrition data"""
    
    current_nutrition_data = {
        'calories_progress': calories_progress,
        'protein_progress': protein_progress,
        'fat_progress': fat_progress,
        'carbs_progress': carbs_progress,
        'sugar_progress': sugar_progress,
        'sodium_progress': sodium_progress,
        'recent_scans_count': recent_scans_count,
        'days_active': days_active
    }
    
    # Get existing active tips
    existing_tips = PersonalizedTip.objects.filter(user=user, is_active=True)
    
    # Check if existing tips are still relevant
    for tip in existing_tips:
        if not tip.is_still_relevant(current_nutrition_data):
            tip.is_active = False
            tip.save()
    
    # Generate new tips based on current conditions
    new_tips_data = generate_personalized_tips(
        dietary_goals, calories_progress, protein_progress, fat_progress, 
        carbs_progress, sugar_progress, sodium_progress, recent_scans_count, days_active
    )
    
    # Create or update persistent tips
    for tip_data in new_tips_data:
        trigger_condition = get_trigger_condition(tip_data)
        
        tip, created = PersonalizedTip.objects.get_or_create(
            user=user,
            trigger_condition=trigger_condition,
            defaults={
                'tip_type': tip_data['type'],
                'priority': tip_data['priority'],
                'icon': tip_data['icon'],
                'color': tip_data['color'],
                'title': tip_data['title'],
                'message': tip_data['message'],
                'last_nutrition_snapshot': current_nutrition_data,
                'is_active': True
            }
        )
        
        if not created and tip.is_active:
            # Update existing tip with current data
            tip.last_nutrition_snapshot = current_nutrition_data
            tip.updated_at = timezone.now()
            tip.save()
    
    # Return active tips ordered by priority
    active_tips = PersonalizedTip.objects.filter(user=user, is_active=True).order_by('priority', '-created_at')[:5]
    
    # Convert to format expected by template
    return [
        {
            'type': tip.tip_type,
            'icon': tip.icon,
            'color': tip.color,
            'title': tip.title,
            'message': tip.message,
            'priority': tip.priority,
            'created_at': tip.created_at,
            'updated_at': tip.updated_at
        }
        for tip in active_tips
    ]

def get_trigger_condition(tip_data):
    """Generate trigger condition string based on tip data"""
    title = tip_data['title'].lower()
    
    if 'sugar' in title and 'critical' in title:
        return 'sugar_progress > 90'
    elif 'sodium' in title and 'alert' in title:
        return 'sodium_progress > 90'
    elif 'protein' in title and 'boost' in title:
        return 'protein_progress < 50'
    elif 'calorie' in title and 'low' in title:
        return 'calories_progress < 40'
    elif 'fat' in title and 'high' in title:
        return 'fat_progress > 85'
    elif 'scanning' in title and 'champion' in title:
        return f'recent_scans >= 10'
    elif 'start scanning' in title:
        return 'recent_scans == 0'
    elif 'milestone' in title:
        return f'days_active >= 30'
    else:
        return f'general_tip_{tip_data["priority"]}'

@login_required
@require_POST
def refresh_personalized_tips(request):
    """Refresh personalized tips for the user"""
    try:
        # Get user's current dietary goals and progress
        dietary_goals = DietaryGoal.objects.filter(user=request.user).first()
        if not dietary_goals:
            return JsonResponse({'success': False, 'error': 'No dietary goals found'})
        
        # Calculate current progress
        calories_progress = (dietary_goals.calories_consumed / dietary_goals.calories_target * 100) if dietary_goals.calories_target > 0 else 0
        protein_progress = (dietary_goals.protein_consumed / dietary_goals.protein_target * 100) if dietary_goals.protein_target > 0 else 0
        fat_progress = (dietary_goals.fat_consumed / dietary_goals.fat_target * 100) if dietary_goals.fat_target > 0 else 0
        carbs_progress = (dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100) if dietary_goals.carbs_target > 0 else 0
        
        # Get recent activity stats
        recent_scans_count = ScanHistory.objects.filter(
            user=request.user, 
            scanned_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        days_active = (timezone.now().date() - request.user.date_joined.date()).days
        
        # Clear existing tips and generate new ones
        PersonalizedTip.objects.filter(user=request.user).delete()
        
        # Generate fresh tips
        personalized_tips = get_or_create_persistent_tips(
            request.user, dietary_goals, calories_progress, protein_progress, 
            fat_progress, carbs_progress, 0, 0, recent_scans_count, days_active
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Personalized tips refreshed successfully!',
            'tips_count': len(personalized_tips)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def update_nutrition_goals(request):
    """Update user's nutrition goals with proper redirect handling"""
    try:
        dietary_goals, created = DietaryGoal.objects.get_or_create(user=request.user)
        
        # Validate and update goals from form data with proper bounds checking
        calories_target = int(request.POST.get('calories_target', 2000))
        protein_target = int(request.POST.get('protein_target', 50))
        fat_target = int(request.POST.get('fat_target', 70))
        carbs_target = int(request.POST.get('carbs_target', 300))
        sugar_target = int(request.POST.get('sugar_target', 50))
        sodium_target = int(request.POST.get('sodium_target', 2300))
        
        # Validate ranges
        if not (500 <= calories_target <= 5000):
            error_msg = 'Calories target must be between 500 and 5000'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('accounts:dashboard')
            
        if not (10 <= protein_target <= 300):
            error_msg = 'Protein target must be between 10 and 300g'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('accounts:dashboard')
            
        if not (10 <= fat_target <= 200):
            error_msg = 'Fat target must be between 10 and 200g'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('accounts:dashboard')
            
        if not (50 <= carbs_target <= 800):
            error_msg = 'Carbs target must be between 50 and 800g'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('accounts:dashboard')
            
        if not (10 <= sugar_target <= 200):
            error_msg = 'Sugar target must be between 10 and 200g'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('accounts:dashboard')
            
        if not (500 <= sodium_target <= 5000):
            error_msg = 'Sodium target must be between 500 and 5000mg'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return redirect('accounts:dashboard')
        
        dietary_goals.calories_target = calories_target
        dietary_goals.protein_target = protein_target
        dietary_goals.fat_target = fat_target
        dietary_goals.carbs_target = carbs_target
        dietary_goals.sugar_target = sugar_target
        dietary_goals.sodium_target = sodium_target
        dietary_goals.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Return JSON for AJAX requests
            calories_progress = min((dietary_goals.calories_consumed / dietary_goals.calories_target * 100), 100) if dietary_goals.calories_target > 0 else 0
            protein_progress = min((dietary_goals.protein_consumed / dietary_goals.protein_target * 100), 100) if dietary_goals.protein_target > 0 else 0
            fat_progress = min((dietary_goals.fat_consumed / dietary_goals.fat_target * 100), 100) if dietary_goals.fat_target > 0 else 0
            carbs_progress = min((dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100), 100) if dietary_goals.carbs_target > 0 else 0
            sugar_progress = min((dietary_goals.sugar_consumed / dietary_goals.sugar_target * 100), 100) if dietary_goals.sugar_target > 0 else 0
            sodium_progress = min((dietary_goals.sodium_consumed / dietary_goals.sodium_target * 100), 100) if dietary_goals.sodium_target > 0 else 0
            
            return JsonResponse({
                'success': True,
                'message': 'Your nutrition goals have been updated successfully!',
                'progress': {
                    'calories': calories_progress,
                    'protein': protein_progress,
                    'fat': fat_progress,
                    'carbs': carbs_progress,
                    'sugar': sugar_progress,
                    'sodium': sodium_progress
                },
                'remaining': {
                    'calories': max(0, dietary_goals.calories_target - dietary_goals.calories_consumed),
                    'protein': max(0, dietary_goals.protein_target - dietary_goals.protein_consumed),
                    'fat': max(0, dietary_goals.fat_target - dietary_goals.fat_consumed),
                    'carbs': max(0, dietary_goals.carbs_target - dietary_goals.carbs_consumed),
                    'sugar': max(0, dietary_goals.sugar_target - dietary_goals.sugar_consumed),
                    'sodium': max(0, dietary_goals.sodium_target - dietary_goals.sodium_consumed)
                }
            })
        else:
            messages.success(request, 'Your nutrition goals have been updated successfully!')
            return redirect('accounts:dashboard')
        
    except (ValueError, TypeError) as e:
        error_msg = 'Invalid input values. Please enter valid numbers.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect('accounts:dashboard')
    except Exception as e:
        error_msg = f'An error occurred: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_msg})
        messages.error(request, error_msg)
        return redirect('accounts:dashboard')

@login_required
@require_POST
def reset_daily_goals(request):
    """Reset daily nutrition consumption to zero"""
    try:
        dietary_goals = DietaryGoal.objects.get(user=request.user)
        dietary_goals.calories_consumed = 0
        dietary_goals.protein_consumed = 0
        dietary_goals.fat_consumed = 0
        dietary_goals.carbs_consumed = 0
        dietary_goals.sugar_consumed = 0
        dietary_goals.sodium_consumed = 0
        dietary_goals.last_reset_date = timezone.now().date()
        dietary_goals.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Daily nutrition tracking has been reset to zero!',
            'progress': {
                'calories': 0,
                'protein': 0,
                'fat': 0,
                'carbs': 0,
                'sugar': 0,
                'sodium': 0
            },
            'consumed': {
                'calories': 0,
                'protein': 0,
                'fat': 0,
                'carbs': 0,
                'sugar': 0,
                'sodium': 0
            },
            'remaining': {
                'calories': dietary_goals.calories_target,
                'protein': dietary_goals.protein_target,
                'fat': dietary_goals.fat_target,
                'carbs': dietary_goals.carbs_target,
                'sugar': dietary_goals.sugar_target,
                'sodium': dietary_goals.sodium_target
            }
        })
    except DietaryGoal.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No dietary goals found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def apply_preset_goals(request):
    """Apply preset nutrition goals (Weight Loss, Maintenance, Muscle Gain)"""
    try:
        data = json.loads(request.body)
        preset_type = data.get('preset_type', '').lower()
        
        preset_values = {
            'weight_loss': {
                'calories_target': 1500,
                'protein_target': 120,
                'fat_target': 50,
                'carbs_target': 150,
                'sugar_target': 30,
                'sodium_target': 2000,
            },
            'maintenance': {
                'calories_target': 2000,
                'protein_target': 100,
                'fat_target': 70,
                'carbs_target': 250,
                'sugar_target': 50,
                'sodium_target': 2300,
            },
            'muscle_gain': {
                'calories_target': 2500,
                'protein_target': 150,
                'fat_target': 85,
                'carbs_target': 350,
                'sugar_target': 60,
                'sodium_target': 2500,
            }
        }
        
        if preset_type not in preset_values:
            return JsonResponse({'success': False, 'error': 'Invalid preset type'})
        
        # Get or create dietary goals
        dietary_goals, created = DietaryGoal.objects.get_or_create(user=request.user)
        
        preset = preset_values[preset_type]
        dietary_goals.calories_target = preset['calories_target']
        dietary_goals.protein_target = preset['protein_target']
        dietary_goals.fat_target = preset['fat_target']
        dietary_goals.carbs_target = preset['carbs_target']
        dietary_goals.sugar_target = preset['sugar_target']
        dietary_goals.sodium_target = preset['sodium_target']
        dietary_goals.save()
        
        # Calculate new progress percentages
        calories_progress = min((dietary_goals.calories_consumed / dietary_goals.calories_target * 100), 100) if dietary_goals.calories_target > 0 else 0
        protein_progress = min((dietary_goals.protein_consumed / dietary_goals.protein_target * 100), 100) if dietary_goals.protein_target > 0 else 0
        fat_progress = min((dietary_goals.fat_consumed / dietary_goals.fat_target * 100), 100) if dietary_goals.fat_target > 0 else 0
        carbs_progress = min((dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100), 100) if dietary_goals.carbs_target > 0 else 0
        sugar_progress = min((dietary_goals.sugar_consumed / dietary_goals.sugar_target * 100), 100) if dietary_goals.sugar_target > 0 else 0
        sodium_progress = min((dietary_goals.sodium_consumed / dietary_goals.sodium_target * 100), 100) if dietary_goals.sodium_target > 0 else 0
        
        preset_name = preset_type.replace('_', ' ').title()
        
        return JsonResponse({
            'success': True,
            'message': f'{preset_name} goals applied successfully!',
            'goals': {
                'calories_target': dietary_goals.calories_target,
                'protein_target': dietary_goals.protein_target,
                'fat_target': dietary_goals.fat_target,
                'carbs_target': dietary_goals.carbs_target,
                'sugar_target': dietary_goals.sugar_target,
                'sodium_target': dietary_goals.sodium_target,
            },
            'progress': {
                'calories': calories_progress,
                'protein': protein_progress,
                'fat': fat_progress,
                'carbs': carbs_progress,
                'sugar': sugar_progress,
                'sodium': sodium_progress
            },
            'remaining': {
                'calories': max(0, dietary_goals.calories_target - dietary_goals.calories_consumed),
                'protein': max(0, dietary_goals.protein_target - dietary_goals.protein_consumed),
                'fat': max(0, dietary_goals.fat_target - dietary_goals.fat_consumed),
                'carbs': max(0, dietary_goals.carbs_target - dietary_goals.carbs_consumed),
                'sugar': max(0, dietary_goals.sugar_target - dietary_goals.sugar_consumed),
                'sodium': max(0, dietary_goals.sodium_target - dietary_goals.sodium_consumed)
            }
        })
        
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': 'Invalid input values'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})

@login_required
def profile(request):
    """User profile view"""
    return render(request, 'accounts/profile.html', {'user': request.user})

@login_required
def add_remove_favorite(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)
    user = request.user
    
    if request.method == 'POST':
        try:
            favorite = FavoriteProduct.objects.get(user=user, product=product)
            favorite.delete()
            messages.info(request, f'"{product.name}" removed from favorites.')
        except FavoriteProduct.DoesNotExist:
            FavoriteProduct.objects.create(user=user, product=product)
            messages.success(request, f'"{product.name}" added to favorites!')
    return redirect('scanner:product_detail', barcode=barcode)

@login_required
def add_review(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text', '')

        if rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:
                    ProductReview.objects.update_or_create(
                        user=request.user,
                        product=product,
                        defaults={'rating': rating, 'review_text': review_text}
                    )
                    messages.success(request, 'Your review has been submitted!')
                else:
                    messages.error(request, 'Rating must be between 1 and 5.')
            except ValueError:
                messages.error(request, 'Invalid rating value.')
        else:
            messages.error(request, 'Please provide a rating for your review.')
    return redirect('scanner:product_detail', barcode=barcode)

@login_required
@require_POST
def add_to_nutrition_tracker(request):
    """Add product nutrition to user's daily tracking with confirmation toast"""
    try:
        data = json.loads(request.body)
        barcode = data.get('barcode')
        serving_size = float(data.get('serving_size', 100))
        
        product = get_object_or_404(Product, barcode=barcode)
        dietary_goals, created = DietaryGoal.objects.get_or_create(user=request.user)
        
        tracked_item = TrackedItem.objects.create(
            user=request.user,
            product=product,
            serving_size=serving_size
        )
        
        # Calculate nutrition values based on serving size
        if product.nutrition_info:
            nutrition = product.nutrition_info
            multiplier = serving_size / 100  # Nutrition info is per 100g
            
            # Add to daily consumption
            dietary_goals.calories_consumed += int(nutrition.get('energy-kcal_100g', 0) * multiplier)
            dietary_goals.protein_consumed += int(nutrition.get('proteins_100g', 0) * multiplier)
            dietary_goals.fat_consumed += int(nutrition.get('fat_100g', 0) * multiplier)
            dietary_goals.carbs_consumed += int(nutrition.get('carbohydrates_100g', 0) * multiplier)
            dietary_goals.sugar_consumed += int(nutrition.get('sugars_100g', 0) * multiplier)
            dietary_goals.sodium_consumed += int(nutrition.get('sodium_100g', 0) * multiplier)
            dietary_goals.save()
            
            return JsonResponse({
                'success': True,
                'message': f'✅ Added {product.name} to your nutrition tracker!',
                'product_info': {
                    'name': product.name,
                    'health_score': product.health_score,
                    'nova_group': product.nova_group,
                    'serving_size': serving_size
                },
                'nutrition_added': {
                    'calories': int(nutrition.get('energy-kcal_100g', 0) * multiplier),
                    'protein': int(nutrition.get('proteins_100g', 0) * multiplier),
                    'fat': int(nutrition.get('fat_100g', 0) * multiplier),
                    'carbs': int(nutrition.get('carbohydrates_100g', 0) * multiplier)
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No nutrition information available for this product'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def remove_tracked_item(request):
    """Remove item from nutrition tracker"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        tracked_item = get_object_or_404(TrackedItem, id=item_id, user=request.user)
        
        # Remove nutrition from daily goals
        dietary_goals = DietaryGoal.objects.get(user=request.user)
        calculated_nutrition = tracked_item.calculated_nutrition
        
        if calculated_nutrition:
            dietary_goals.calories_consumed -= int(calculated_nutrition.get('energy-kcal_100g', 0))
            dietary_goals.protein_consumed -= int(calculated_nutrition.get('proteins_100g', 0))
            dietary_goals.fat_consumed -= int(calculated_nutrition.get('fat_100g', 0))
            dietary_goals.carbs_consumed -= int(calculated_nutrition.get('carbohydrates_100g', 0))
            dietary_goals.sugar_consumed -= int(calculated_nutrition.get('sugars_100g', 0))
            dietary_goals.sodium_consumed -= int(calculated_nutrition.get('sodium_100g', 0))
            
            # Ensure values don't go negative
            dietary_goals.calories_consumed = max(0, dietary_goals.calories_consumed)
            dietary_goals.protein_consumed = max(0, dietary_goals.protein_consumed)
            dietary_goals.fat_consumed = max(0, dietary_goals.fat_consumed)
            dietary_goals.carbs_consumed = max(0, dietary_goals.carbs_consumed)
            dietary_goals.sugar_consumed = max(0, dietary_goals.sugar_consumed)
            dietary_goals.sodium_consumed = max(0, dietary_goals.sodium_consumed)
            
            dietary_goals.save()
        
        tracked_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Removed {tracked_item.product.name} from tracker'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def add_manual_nutrition(request):
    """Add manual nutrition entries to user's daily tracking"""
    try:
        data = json.loads(request.body)
        
        # Get nutrition values from request
        calories = float(data.get('calories', 0))
        protein = float(data.get('protein', 0))
        fat = float(data.get('fat', 0))
        carbs = float(data.get('carbs', 0))
        sugar = float(data.get('sugar', 0))
        sodium = float(data.get('sodium', 0))
        
        # Validate input ranges
        if calories < 0 or calories > 2000:
            return JsonResponse({'success': False, 'error': 'Calories must be between 0 and 2000'})
        if protein < 0 or protein > 200:
            return JsonResponse({'success': False, 'error': 'Protein must be between 0 and 200g'})
        if fat < 0 or fat > 150:
            return JsonResponse({'success': False, 'error': 'Fat must be between 0 and 150g'})
        if carbs < 0 or carbs > 300:
            return JsonResponse({'success': False, 'error': 'Carbs must be between 0 and 300g'})
        if sugar < 0 or sugar > 100:
            return JsonResponse({'success': False, 'error': 'Sugar must be between 0 and 100g'})
        if sodium < 0 or sodium > 3000:
            return JsonResponse({'success': False, 'error': 'Sodium must be between 0 and 3000mg'})
        
        # Get or create dietary goals
        dietary_goals, created = DietaryGoal.objects.get_or_create(user=request.user)
        
        # Add to daily consumption
        dietary_goals.calories_consumed += int(calories)
        dietary_goals.protein_consumed += int(protein)
        dietary_goals.fat_consumed += int(fat)
        dietary_goals.carbs_consumed += int(carbs)
        dietary_goals.sugar_consumed += int(sugar)
        dietary_goals.sodium_consumed += int(sodium)
        dietary_goals.save()
        
        # Calculate new progress percentages
        calories_progress = min((dietary_goals.calories_consumed / dietary_goals.calories_target * 100), 100) if dietary_goals.calories_target > 0 else 0
        protein_progress = min((dietary_goals.protein_consumed / dietary_goals.protein_target * 100), 100) if dietary_goals.protein_target > 0 else 0
        fat_progress = min((dietary_goals.fat_consumed / dietary_goals.fat_target * 100), 100) if dietary_goals.fat_target > 0 else 0
        carbs_progress = min((dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100), 100) if dietary_goals.carbs_target > 0 else 0
        sugar_progress = min((dietary_goals.sugar_consumed / dietary_goals.sugar_target * 100), 100) if dietary_goals.sugar_target > 0 else 0
        sodium_progress = min((dietary_goals.sodium_consumed / dietary_goals.sodium_target * 100), 100) if dietary_goals.sodium_target > 0 else 0
        
        return JsonResponse({
            'success': True,
            'message': 'Manual nutrition entry added successfully!',
            'progress': {
                'calories': calories_progress,
                'protein': protein_progress,
                'fat': fat_progress,
                'carbs': carbs_progress,
                'sugar': sugar_progress,
                'sodium': sodium_progress
            },
            'consumed': {
                'calories': dietary_goals.calories_consumed,
                'protein': dietary_goals.protein_consumed,
                'fat': dietary_goals.fat_consumed,
                'carbs': dietary_goals.carbs_consumed,
                'sugar': dietary_goals.sugar_consumed,
                'sodium': dietary_goals.sodium_consumed
            },
            'remaining': {
                'calories': max(0, dietary_goals.calories_target - dietary_goals.calories_consumed),
                'protein': max(0, dietary_goals.protein_target - dietary_goals.protein_consumed),
                'fat': max(0, dietary_goals.fat_target - dietary_goals.fat_consumed),
                'carbs': max(0, dietary_goals.carbs_target - dietary_goals.carbs_consumed),
                'sugar': max(0, dietary_goals.sugar_target - dietary_goals.sugar_consumed),
                'sodium': max(0, dietary_goals.sodium_target - dietary_goals.sodium_consumed)
            }
        })
        
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': 'Invalid input values. Please enter valid numbers.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})

@require_POST
def toggle_theme(request):
    """Toggle theme between light and dark mode via AJAX"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme', 'light')
        
        # Validate theme value
        if theme not in ['light', 'dark']:
            theme = 'light'
        
        # Store theme in session
        request.session['theme'] = theme
        
        return JsonResponse({
            'status': 'success',
            'theme': theme,
            'message': f'Theme switched to {theme} mode'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        })

@login_required
def weekly_nutrition_report(request):
    """View for detailed weekly nutrition analysis"""
    user = request.user
    from datetime import timedelta
    
    # Get last 4 weeks of data
    today = timezone.now().date()
    four_weeks_ago = today - timedelta(days=28)
    
    weekly_logs = WeeklyNutritionLog.objects.filter(
        user=user,
        week_start_date__gte=four_weeks_ago
    ).order_by('-week_start_date')[:4]
    
    # Get current dietary goals
    dietary_goals = DietaryGoal.objects.filter(user=user).first()
    
    context = {
        'user': user,
        'weekly_logs': weekly_logs,
        'dietary_goals': dietary_goals,
    }
    return render(request, 'accounts/weekly_report.html', context)

def generate_personalized_tips(dietary_goals, calories_progress, protein_progress, fat_progress, 
                             carbs_progress, sugar_progress, sodium_progress, recent_scans_count, days_active):
    """Generate dynamic personalized tips based on user's nutrition data and activity"""
    tips = []
    
    # Critical tips (red warnings) - highest priority
    if sugar_progress > 90:
        tips.append({
            'type': 'critical',
            'icon': 'exclamation-triangle',
            'color': 'danger',
            'title': 'Sugar Intake Critical',
            'message': f'You\'ve consumed {sugar_progress:.0f}% of your daily sugar limit. Consider reducing sugary foods.',
            'priority': 1
        })
    
    if sodium_progress > 90:
        tips.append({
            'type': 'critical',
            'icon': 'exclamation-triangle',
            'color': 'danger',
            'title': 'High Sodium Alert',
            'message': f'You\'re at {sodium_progress:.0f}% of your sodium limit. Choose low-sodium alternatives.',
            'priority': 1
        })
    
    # Warning tips (yellow/orange) - medium priority
    if protein_progress < 50:
        protein_needed = dietary_goals.protein_target - dietary_goals.protein_consumed
        tips.append({
            'type': 'warning',
            'icon': 'exclamation-circle',
            'color': 'warning',
            'title': 'Boost Your Protein',
            'message': f'You need {protein_needed:.0f}g more protein today. Try lean meats, beans, or nuts.',
            'priority': 2
        })
    
    if calories_progress < 40:
        calories_needed = dietary_goals.calories_target - dietary_goals.calories_consumed
        tips.append({
            'type': 'warning',
            'icon': 'info-circle',
            'color': 'info',
            'title': 'Calorie Goal Low',
            'message': f'You\'re {calories_needed:.0f} calories under your goal. Consider adding a healthy snack.',
            'priority': 2
        })
    
    if fat_progress > 85:
        tips.append({
            'type': 'warning',
            'icon': 'exclamation-circle',
            'color': 'warning',
            'title': 'Fat Intake High',
            'message': 'You\'re close to your daily fat limit. Choose lean proteins for remaining meals.',
            'priority': 2
        })
    
    # Positive reinforcement (green) - encouraging messages
    if 80 <= calories_progress <= 100:
        tips.append({
            'type': 'success',
            'icon': 'check-circle',
            'color': 'success',
            'title': 'Perfect Calorie Balance',
            'message': 'Excellent! You\'re right on track with your calorie goal today.',
            'priority': 3
        })
    
    if protein_progress >= 80:
        tips.append({
            'type': 'success',
            'icon': 'check-circle',
            'color': 'success',
            'title': 'Protein Goal Achieved',
            'message': 'Great job meeting your protein target! Your muscles will thank you.',
            'priority': 3
        })
    
    if sugar_progress <= 30:
        tips.append({
            'type': 'success',
            'icon': 'check-circle',
            'color': 'success',
            'title': 'Low Sugar Success',
            'message': 'Excellent! You\'re keeping your sugar intake low today.',
            'priority': 3
        })
    
    # Activity-based tips
    if recent_scans_count == 0:
        tips.append({
            'type': 'info',
            'icon': 'camera',
            'color': 'primary',
            'title': 'Start Scanning',
            'message': 'Scan your first product this week to track your nutrition automatically!',
            'priority': 2
        })
    elif recent_scans_count >= 10:
        tips.append({
            'type': 'success',
            'icon': 'graph-up',
            'color': 'success',
            'title': 'Scanning Champion',
            'message': f'Amazing! You\'ve scanned {recent_scans_count} products this week. Keep it up!',
            'priority': 3
        })
    elif recent_scans_count >= 5:
        tips.append({
            'type': 'info',
            'icon': 'graph-up',
            'color': 'info',
            'title': 'Good Progress',
            'message': f'You\'ve scanned {recent_scans_count} products this week. Great tracking!',
            'priority': 3
        })
    
    # Milestone tips
    if days_active >= 30:
        tips.append({
            'type': 'success',
            'icon': 'trophy',
            'color': 'success',
            'title': 'Monthly Milestone',
            'message': f'Congratulations! You\'ve been tracking nutrition for {days_active} days.',
            'priority': 3
        })
    elif days_active >= 7:
        tips.append({
            'type': 'info',
            'icon': 'calendar-check',
            'color': 'info',
            'title': 'Week Strong',
            'message': f'You\'ve been consistent for {days_active} days. Keep building the habit!',
            'priority': 3
        })
    
    # General nutrition tips if no specific issues
    if len(tips) < 3:
        general_tips = [
            {
                'type': 'info',
                'icon': 'droplet',
                'color': 'info',
                'title': 'Stay Hydrated',
                'message': 'Remember to drink 8 glasses of water throughout the day.',
                'priority': 4
            },
            {
                'type': 'info',
                'icon': 'apple',
                'color': 'info',
                'title': 'Eat the Rainbow',
                'message': 'Include colorful fruits and vegetables in your meals for better nutrition.',
                'priority': 4
            },
            {
                'type': 'info',
                'icon': 'clock',
                'color': 'info',
                'title': 'Meal Timing',
                'message': 'Try to eat regular meals every 3-4 hours to maintain energy levels.',
                'priority': 4
            }
        ]
        tips.extend(general_tips)
    
    # Sort by priority (1 = highest, 4 = lowest) and limit to 5 tips
    tips.sort(key=lambda x: x['priority'])
    return tips[:5]

@login_required
@require_POST
def export_nutrition_data(request):
    """Export user's nutrition data as PDF"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from django.http import HttpResponse
        import io
        from datetime import datetime
        
        # Create the HttpResponse object with PDF headers
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="nutrition-data-export.pdf"'
        
        # Create the PDF object
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        
        # Add title
        title = Paragraph(f"Nutrition Data Export - {request.user.username}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Add export date
        date_para = Paragraph(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 12))
        
        # Get user's dietary goals
        dietary_goals = DietaryGoal.objects.filter(user=request.user).first()
        if dietary_goals:
            # Nutrition Goals Table
            goals_title = Paragraph("Current Nutrition Goals", styles['Heading2'])
            elements.append(goals_title)
            
            goals_data = [
                ['Nutrient', 'Target', 'Consumed', 'Remaining'],
                ['Calories', f"{dietary_goals.calories_target} kcal", f"{dietary_goals.calories_consumed} kcal", f"{max(0, dietary_goals.calories_target - dietary_goals.calories_consumed)} kcal"],
                ['Protein', f"{dietary_goals.protein_target}g", f"{dietary_goals.protein_consumed}g", f"{max(0, dietary_goals.protein_target - dietary_goals.protein_consumed)}g"],
                ['Fat', f"{dietary_goals.fat_target}g", f"{dietary_goals.fat_consumed}g", f"{max(0, dietary_goals.fat_target - dietary_goals.fat_consumed)}g"],
                ['Carbs', f"{dietary_goals.carbs_target}g", f"{dietary_goals.carbs_consumed}g", f"{max(0, dietary_goals.carbs_target - dietary_goals.carbs_consumed)}g"],
                ['Sugar', f"{dietary_goals.sugar_target}g", f"{dietary_goals.sugar_consumed}g", f"{max(0, dietary_goals.sugar_target - dietary_goals.sugar_consumed)}g"],
                ['Sodium', f"{dietary_goals.sodium_target}mg", f"{dietary_goals.sodium_consumed}mg", f"{max(0, dietary_goals.sodium_target - dietary_goals.sodium_consumed)}mg"],
            ]
            
            goals_table = Table(goals_data)
            goals_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(goals_table)
            elements.append(Spacer(1, 12))
        
        # Get tracked items
        tracked_items = TrackedItem.objects.filter(user=request.user).select_related('product')[:20]
        if tracked_items:
            tracked_title = Paragraph("Recent Tracked Items", styles['Heading2'])
            elements.append(tracked_title)
            
            tracked_data = [['Product Name', 'Brand', 'Serving Size', 'Date Added']]
            for item in tracked_items:
                tracked_data.append([
                    item.product.name[:30] + "..." if len(item.product.name) > 30 else item.product.name,
                    item.product.brand[:20] + "..." if item.product.brand and len(item.product.brand) > 20 else (item.product.brand or "N/A"),
                    f"{item.serving_size}g",
                    item.added_at.strftime('%Y-%m-%d')
                ])
            
            tracked_table = Table(tracked_data)
            tracked_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(tracked_table)
            elements.append(Spacer(1, 12))
        
        # Get favorite products
        favorites = FavoriteProduct.objects.filter(user=request.user).select_related('product')[:10]
        if favorites:
            fav_title = Paragraph("Favorite Products", styles['Heading2'])
            elements.append(fav_title)
            
            fav_data = [['Product Name', 'Brand', 'Health Score', 'Date Added']]
            for fav in favorites:
                fav_data.append([
                    fav.product.name[:30] + "..." if len(fav.product.name) > 30 else fav.product.name,
                    fav.product.brand[:20] + "..." if fav.product.brand and len(fav.product.brand) > 20 else (fav.product.brand or "N/A"),
                    str(fav.product.health_score) if fav.product.health_score else "N/A",
                    fav.added_at.strftime('%Y-%m-%d')
                ])
            
            fav_table = Table(fav_data)
            fav_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(fav_table)
        
        # Build PDF
        doc.build(elements)
        
        # Get the value of the BytesIO buffer and write it to the response
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        
        return response
        
    except ImportError:
        return JsonResponse({
            'success': False, 
            'error': 'PDF generation library not available. Please install reportlab: pip install reportlab'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error generating PDF: {str(e)}'})

@login_required
@require_POST
def generate_ai_tips_view(request):
    """Generate AI-powered personalized tips via AJAX"""
    try:
        from .ai_tips import get_ai_personalized_tips
        
        user = request.user
        
        # Get user's dietary goals and current progress
        dietary_goals = DietaryGoal.objects.filter(user=user).first()
        if not dietary_goals:
            return JsonResponse({
                'success': False,
                'message': 'Please set your dietary goals first to generate personalized tips.'
            })
        
        # Calculate current progress
        calories_progress = (dietary_goals.calories_consumed / dietary_goals.calories_target * 100) if dietary_goals.calories_target > 0 else 0
        protein_progress = (dietary_goals.protein_consumed / dietary_goals.protein_target * 100) if dietary_goals.protein_target > 0 else 0
        fat_progress = (dietary_goals.fat_consumed / dietary_goals.fat_target * 100) if dietary_goals.fat_target > 0 else 0
        carbs_progress = (dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100) if dietary_goals.carbs_target > 0 else 0
        
        progress_data = {
            'calories_progress': calories_progress,
            'protein_progress': protein_progress,
            'fat_progress': fat_progress,
            'carbs_progress': carbs_progress
        }
        
        # Get activity data
        recent_scans = ScanHistory.objects.filter(
            user=user,
            scanned_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        activity_data = {
            'recent_scans_count': recent_scans,
            'days_active': 7  # Simplified for now
        }
        
        # Generate AI tips
        tips = get_ai_personalized_tips(user, dietary_goals, progress_data, activity_data)
        
        return JsonResponse({
            'success': True,
            'message': f'Generated {len(tips)} personalized AI tips successfully!',
            'tips_count': len(tips)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to generate AI tips: {str(e)}'
        })

@login_required
@require_POST
def generate_ml_insights_view(request):
    """Generate ML insights and analysis via AJAX"""
    try:
        from .ml_insights import get_ml_insights
        
        user = request.user
        
        # Generate ML insights regardless of data amount
        insights = get_ml_insights(user)
        
        if insights.get('basic_analysis'):
            return JsonResponse({
                'success': True,
                'message': 'Nutrition analysis completed successfully! Keep tracking for more detailed insights.',
                'analysis_type': 'basic'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Advanced ML analysis completed successfully!',
                'analysis_type': 'advanced',
                'has_visualizations': 'visualizations' in insights
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to generate ML insights: {str(e)}'
        })
