from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.db.models import Avg

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

    # Fetch favorite products
    favorite_products = FavoriteProduct.objects.filter(user=user).select_related('product')[:10]

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
    }
    return render(request, 'accounts/dashboard.html', context)

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
