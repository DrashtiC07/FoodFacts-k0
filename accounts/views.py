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
from .models import CustomUser, ProductReview, FavoriteProduct, DietaryGoal, WeeklyNutritionLog
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

    personalized_tips = generate_personalized_tips(
        dietary_goals, calories_progress, protein_progress, fat_progress, 
        carbs_progress, sugar_progress, sodium_progress, recent_scans_count, days_active
    )

    context = {
        'user': user,
        'scan_history': scan_history,
        'favorite_products': favorite_products,
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
    """Add product nutrition to user's daily tracking"""
    try:
        data = json.loads(request.body)
        barcode = data.get('barcode')
        serving_size = float(data.get('serving_size', 100))
        
        product = get_object_or_404(Product, barcode=barcode)
        dietary_goals, created = DietaryGoal.objects.get_or_create(user=request.user)
        
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
                'message': f'Added {product.name} to your nutrition tracker!'
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
    ).order_by('-week_start_date')
    
    # Get current dietary goals
    dietary_goals = DietaryGoal.objects.filter(user=user).first()
    
    context = {
        'user': user,
        'weekly_logs': weekly_logs,
        'dietary_goals': dietary_goals,
    }
    return render(request, 'accounts/weekly_report.html', context)
