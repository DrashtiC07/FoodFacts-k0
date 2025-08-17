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
from .models import CustomUser, ProductReview, FavoriteProduct, DietaryGoal, WeeklyNutritionLog, DailyNutritionSnapshot
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

    # Fetch favorite products
    favorite_products = FavoriteProduct.objects.filter(
        user=user, 
        product__barcode__isnull=False,
        product__barcode__gt=''
    ).select_related('product')[:10]

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
            'fiber_target': 25,
            'saturated_fat_target': 20,
        }
    )

    dietary_goals.reset_daily_if_needed()

    nutrients = ['calories', 'protein', 'fat', 'carbs', 'sugar', 'sodium', 'fiber', 'saturated_fat']
    progress_data = {}
    remaining_data = {}
    
    for nutrient in nutrients:
        progress_data[f"{nutrient}_progress"] = dietary_goals.get_progress_percentage(nutrient)
        consumed = getattr(dietary_goals, f"{nutrient}_consumed", 0)
        target = getattr(dietary_goals, f"{nutrient}_target", 0)
        remaining_data[f"{nutrient}_remaining"] = max(0, target - consumed)

    week_ago = timezone.now() - timedelta(days=7)
    recent_scans_count = ScanHistory.objects.filter(user=user, scanned_at__gte=week_ago).count()
    
    # Get last 7 days of nutrition snapshots for trend analysis
    last_week_snapshots = DailyNutritionSnapshot.objects.filter(
        user=user,
        date__gte=week_ago.date()
    ).order_by('-date')[:7]

    # Calculate days active
    days_active = (timezone.now().date() - user.date_joined.date()).days

    weekly_avg_calories = 0
    weekly_avg_sugar = 0
    if last_week_snapshots:
        weekly_avg_calories = sum(s.calories for s in last_week_snapshots) / len(last_week_snapshots)
        weekly_avg_sugar = sum(s.sugar for s in last_week_snapshots) / len(last_week_snapshots)

    context = {
        'user': user,
        'scan_history': scan_history,
        'favorite_products': favorite_products,
        'user_reviews': user_reviews,
        'dietary_goals': dietary_goals,
        'recent_scans_count': recent_scans_count,
        'days_active': days_active,
        'last_week_snapshots': last_week_snapshots,
        'weekly_avg_calories': round(weekly_avg_calories, 1),
        'weekly_avg_sugar': round(weekly_avg_sugar, 1),
        **progress_data,
        **remaining_data,
    }
    return render(request, 'accounts/dashboard.html', context)

@login_required
@require_POST
def update_nutrition_goals(request):
    """Update user's nutrition goals via AJAX with enhanced error handling"""
    try:
        dietary_goals, created = DietaryGoal.objects.get_or_create(user=request.user)
        
        # Validate and update goals from form data with proper bounds checking
        calories_target = int(request.POST.get('calories_target', 2000))
        protein_target = int(request.POST.get('protein_target', 50))
        fat_target = int(request.POST.get('fat_target', 70))
        carbs_target = int(request.POST.get('carbs_target', 300))
        sugar_target = int(request.POST.get('sugar_target', 50))
        sodium_target = int(request.POST.get('sodium_target', 2300))
        fiber_target = int(request.POST.get('fiber_target', 25))
        saturated_fat_target = int(request.POST.get('saturated_fat_target', 20))
        
        # Validate ranges
        if not (500 <= calories_target <= 5000):
            return JsonResponse({'success': False, 'error': 'Calories target must be between 500 and 5000'})
        if not (10 <= protein_target <= 300):
            return JsonResponse({'success': False, 'error': 'Protein target must be between 10 and 300g'})
        if not (10 <= fat_target <= 200):
            return JsonResponse({'success': False, 'error': 'Fat target must be between 10 and 200g'})
        if not (50 <= carbs_target <= 800):
            return JsonResponse({'success': False, 'error': 'Carbs target must be between 50 and 800g'})
        if not (10 <= sugar_target <= 200):
            return JsonResponse({'success': False, 'error': 'Sugar target must be between 10 and 200g'})
        if not (500 <= sodium_target <= 5000):
            return JsonResponse({'success': False, 'error': 'Sodium target must be between 500 and 5000mg'})
        if not (10 <= fiber_target <= 100):
            return JsonResponse({'success': False, 'error': 'Fiber target must be between 10 and 100g'})
        if not (5 <= saturated_fat_target <= 50):
            return JsonResponse({'success': False, 'error': 'Saturated fat target must be between 5 and 50g'})
        
        # Update goals
        dietary_goals.calories_target = calories_target
        dietary_goals.protein_target = protein_target
        dietary_goals.fat_target = fat_target
        dietary_goals.carbs_target = carbs_target
        dietary_goals.sugar_target = sugar_target
        dietary_goals.sodium_target = sodium_target
        dietary_goals.fiber_target = fiber_target
        dietary_goals.saturated_fat_target = saturated_fat_target
        dietary_goals.save()
        
        # Calculate new progress percentages for response
        nutrients = ['calories', 'protein', 'fat', 'carbs', 'sugar', 'sodium', 'fiber', 'saturated_fat']
        progress = {}
        remaining = {}
        
        for nutrient in nutrients:
            progress[nutrient] = dietary_goals.get_progress_percentage(nutrient)
            consumed = getattr(dietary_goals, f"{nutrient}_consumed", 0)
            target = getattr(dietary_goals, f"{nutrient}_target", 0)
            remaining[nutrient] = max(0, target - consumed)
        
        return JsonResponse({
            'success': True,
            'message': 'Your nutrition goals have been updated successfully!',
            'progress': progress,
            'remaining': remaining
        })
        
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': 'Invalid input values. Please enter valid numbers.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'An error occurred: {str(e)}'})

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
        dietary_goals.fiber_consumed = 0
        dietary_goals.saturated_fat_consumed = 0
        dietary_goals.last_reset_date = timezone.now().date()
        dietary_goals.save()
        
        messages.success(request, 'Daily nutrition tracking has been reset!')
        return JsonResponse({'success': True})
    except DietaryGoal.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No dietary goals found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
        
        # Auto-reset if it's a new day
        dietary_goals.reset_daily_if_needed()
        
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
            dietary_goals.fiber_consumed += int(nutrition.get('fiber_100g', 0) * multiplier)
            dietary_goals.saturated_fat_consumed += int(nutrition.get('saturated-fat_100g', 0) * multiplier)
            dietary_goals.save()
            
            # Create or update daily snapshot
            today = timezone.now().date()
            snapshot, created = DailyNutritionSnapshot.objects.get_or_create(
                user=request.user,
                date=today,
                defaults={
                    'calories_target': dietary_goals.calories_target,
                    'protein_target': dietary_goals.protein_target,
                    'fat_target': dietary_goals.fat_target,
                    'carbs_target': dietary_goals.carbs_target,
                    'sugar_target': dietary_goals.sugar_target,
                    'sodium_target': dietary_goals.sodium_target,
                    'fiber_target': dietary_goals.fiber_target,
                    'saturated_fat_target': dietary_goals.saturated_fat_target,
                }
            )
            
            # Update snapshot with current consumption
            snapshot.calories = dietary_goals.calories_consumed
            snapshot.protein = dietary_goals.protein_consumed
            snapshot.fat = dietary_goals.fat_consumed
            snapshot.carbs = dietary_goals.carbs_consumed
            snapshot.sugar = dietary_goals.sugar_consumed
            snapshot.sodium = dietary_goals.sodium_consumed
            snapshot.fiber = dietary_goals.fiber_consumed
            snapshot.saturated_fat = dietary_goals.saturated_fat_consumed
            snapshot.scans_count = ScanHistory.objects.filter(user=request.user, scanned_at__date=today).count()
            snapshot.save()
            
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
    """Display weekly nutrition trends and analysis"""
    user = request.user
    
    # Get last 4 weeks of data
    four_weeks_ago = timezone.now() - timedelta(weeks=4)
    daily_snapshots = DailyNutritionSnapshot.objects.filter(
        user=user,
        date__gte=four_weeks_ago.date()
    ).order_by('-date')
    
    # Group by weeks
    weeks_data = []
    current_week_start = timezone.now().date() - timedelta(days=timezone.now().weekday())
    
    for week in range(4):
        week_start = current_week_start - timedelta(weeks=week)
        week_end = week_start + timedelta(days=6)
        
        week_snapshots = [s for s in daily_snapshots if week_start <= s.date <= week_end]
        
        if week_snapshots:
            avg_calories = sum(s.calories for s in week_snapshots) / len(week_snapshots)
            avg_sugar = sum(s.sugar for s in week_snapshots) / len(week_snapshots)
            avg_sodium = sum(s.sodium for s in week_snapshots) / len(week_snapshots)
            avg_fiber = sum(s.fiber for s in week_snapshots) / len(week_snapshots)
            total_scans = sum(s.scans_count for s in week_snapshots)
            avg_goal_achievement = sum(s.get_goal_achievement_percentage() for s in week_snapshots) / len(week_snapshots)
            
            weeks_data.append({
                'week_start': week_start,
                'week_end': week_end,
                'days_tracked': len(week_snapshots),
                'avg_calories': round(avg_calories, 1),
                'avg_sugar': round(avg_sugar, 1),
                'avg_sodium': round(avg_sodium, 1),
                'avg_fiber': round(avg_fiber, 1),
                'total_scans': total_scans,
                'avg_goal_achievement': round(avg_goal_achievement, 1),
                'snapshots': week_snapshots
            })
    
    # Get current dietary goals
    dietary_goals = DietaryGoal.objects.filter(user=user).first()
    
    context = {
        'weeks_data': weeks_data,
        'dietary_goals': dietary_goals,
        'user': user,
    }
    
    return render(request, 'accounts/weekly_report.html', context)
