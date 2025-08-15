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
from .models import CustomUser, ProductReview, FavoriteProduct, DietaryGoal
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
        }
    )

    # Calculate progress percentages
    calories_progress = (dietary_goals.calories_consumed / dietary_goals.calories_target * 100) if dietary_goals.calories_target > 0 else 0
    protein_progress = (dietary_goals.protein_consumed / dietary_goals.protein_target * 100) if dietary_goals.protein_target > 0 else 0
    fat_progress = (dietary_goals.fat_consumed / dietary_goals.fat_target * 100) if dietary_goals.fat_target > 0 else 0
    carbs_progress = (dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100) if dietary_goals.carbs_target > 0 else 0

    # Calculate remaining amounts
    calories_remaining = max(0, dietary_goals.calories_target - dietary_goals.calories_consumed)
    protein_remaining = max(0, dietary_goals.protein_target - dietary_goals.protein_consumed)
    fat_remaining = max(0, dietary_goals.fat_target - dietary_goals.fat_consumed)
    carbs_remaining = max(0, dietary_goals.carbs_target - dietary_goals.carbs_consumed)

    # Calculate recent activity stats
    week_ago = timezone.now() - timedelta(days=7)
    recent_scans_count = ScanHistory.objects.filter(user=user, scanned_at__gte=week_ago).count()
    
    # Calculate days active
    days_active = (timezone.now().date() - user.date_joined.date()).days

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
        'calories_remaining': calories_remaining,
        'protein_remaining': protein_remaining,
        'fat_remaining': fat_remaining,
        'carbs_remaining': carbs_remaining,
        'recent_scans_count': recent_scans_count,
        'days_active': days_active,
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
        
        # Validate ranges
        if not (500 <= calories_target <= 5000):
            return JsonResponse({'success': False, 'error': 'Calories target must be between 500 and 5000'})
        if not (10 <= protein_target <= 300):
            return JsonResponse({'success': False, 'error': 'Protein target must be between 10 and 300g'})
        if not (10 <= fat_target <= 200):
            return JsonResponse({'success': False, 'error': 'Fat target must be between 10 and 200g'})
        if not (50 <= carbs_target <= 800):
            return JsonResponse({'success': False, 'error': 'Carbs target must be between 50 and 800g'})
        
        # Update goals
        dietary_goals.calories_target = calories_target
        dietary_goals.protein_target = protein_target
        dietary_goals.fat_target = fat_target
        dietary_goals.carbs_target = carbs_target
        dietary_goals.save()
        
        # Calculate new progress percentages for response
        calories_progress = min((dietary_goals.calories_consumed / dietary_goals.calories_target * 100), 100) if dietary_goals.calories_target > 0 else 0
        protein_progress = min((dietary_goals.protein_consumed / dietary_goals.protein_target * 100), 100) if dietary_goals.protein_target > 0 else 0
        fat_progress = min((dietary_goals.fat_consumed / dietary_goals.fat_target * 100), 100) if dietary_goals.fat_target > 0 else 0
        carbs_progress = min((dietary_goals.carbs_consumed / dietary_goals.carbs_target * 100), 100) if dietary_goals.carbs_target > 0 else 0
        
        return JsonResponse({
            'success': True,
            'message': 'Your nutrition goals have been updated successfully!',
            'progress': {
                'calories': calories_progress,
                'protein': protein_progress,
                'fat': fat_progress,
                'carbs': carbs_progress
            },
            'remaining': {
                'calories': max(0, dietary_goals.calories_target - dietary_goals.calories_consumed),
                'protein': max(0, dietary_goals.protein_target - dietary_goals.protein_consumed),
                'fat': max(0, dietary_goals.fat_target - dietary_goals.fat_consumed),
                'carbs': max(0, dietary_goals.carbs_target - dietary_goals.carbs_consumed)
            }
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
        
        # Calculate nutrition values based on serving size
        if product.nutrition_info:
            nutrition = product.nutrition_info
            multiplier = serving_size / 100  # Nutrition info is per 100g
            
            # Add to daily consumption
            dietary_goals.calories_consumed += int(nutrition.get('energy-kcal_100g', 0) * multiplier)
            dietary_goals.protein_consumed += int(nutrition.get('proteins_100g', 0) * multiplier)
            dietary_goals.fat_consumed += int(nutrition.get('fat_100g', 0) * multiplier)
            dietary_goals.carbs_consumed += int(nutrition.get('carbohydrates_100g', 0) * multiplier)
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
