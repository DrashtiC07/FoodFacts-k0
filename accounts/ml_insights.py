# Machine Learning Insights and Visualization
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, r2_score
import io
import base64
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class NutritionMLAnalyzer:
    def __init__(self):
        self.models = {}
    
    def analyze_nutrition_trends(self, user):
        """Analyze user's nutrition trends using ML"""
        try:
            from .models import WeeklyNutritionLog, DietaryGoal
            
            # Get historical data
            logs = WeeklyNutritionLog.objects.filter(user=user).order_by('week_start_date')
            
            if logs.count() < 1:
                return self._generate_basic_insights(user)
            elif logs.count() < 3:
                return self._generate_enhanced_basic_insights(user, logs)
            
            # Prepare data for analysis
            data = []
            for log in logs:
                data.append({
                    'week': (log.week_start_date - logs.first().week_start_date).days // 7,
                    'calories': log.avg_calories_consumed,
                    'protein': log.avg_protein_consumed,
                    'fat': log.avg_fat_consumed,
                    'carbs': log.avg_carbs_consumed,
                    'goal_achievement': log.goal_achievement_rate
                })
            
            df = pd.DataFrame(data)
            
            # Generate insights
            insights = {
                'trend_analysis': self._analyze_trends(df),
                'goal_prediction': self._predict_goal_achievement(df),
                'nutrition_balance': self._analyze_nutrition_balance(df),
                'visualizations': self._create_visualizations(df, user)
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"ML analysis failed: {e}")
            return self._generate_basic_insights(user)
    
    def _analyze_trends(self, df):
        """Analyze nutrition trends using linear regression"""
        trends = {}
        
        for nutrient in ['calories', 'protein', 'fat', 'carbs']:
            if len(df) >= 3:
                X = df[['week']].values
                y = df[nutrient].values
                
                # Linear regression
                model = LinearRegression()
                model.fit(X, y)
                
                # Calculate trend
                slope = model.coef_[0]
                r2 = r2_score(y, model.predict(X))
                
                trends[nutrient] = {
                    'slope': slope,
                    'direction': 'increasing' if slope > 0 else 'decreasing',
                    'strength': 'strong' if r2 > 0.7 else 'moderate' if r2 > 0.4 else 'weak',
                    'r2_score': r2
                }
        
        return trends
    
    def _predict_goal_achievement(self, df):
        """Predict goal achievement using logistic regression"""
        try:
            if len(df) < 4:
                return {'prediction': 'insufficient_data'}
            
            # Prepare features
            X = df[['calories', 'protein', 'fat', 'carbs']].values
            y = (df['goal_achievement'] > 0.8).astype(int)  # Binary: high achievement or not
            
            if len(np.unique(y)) < 2:
                return {'prediction': 'consistent_performance'}
            
            # Train model
            model = LogisticRegression()
            model.fit(X, y)
            
            # Predict next week
            last_week_data = X[-1:].reshape(1, -1)
            prediction = model.predict_proba(last_week_data)[0][1]
            
            return {
                'prediction': 'high_achievement' if prediction > 0.7 else 'needs_improvement',
                'confidence': prediction,
                'factors': self._get_important_factors(model, ['calories', 'protein', 'fat', 'carbs'])
            }
            
        except Exception as e:
            logger.error(f"Goal prediction failed: {e}")
            return {'prediction': 'analysis_error'}
    
    def _analyze_nutrition_balance(self, df):
        """Analyze nutrition balance and provide recommendations"""
        latest_data = df.iloc[-1]
        
        # Calculate ratios
        total_macros = latest_data['protein'] + latest_data['fat'] + latest_data['carbs']
        
        if total_macros > 0:
            protein_ratio = latest_data['protein'] / total_macros
            fat_ratio = latest_data['fat'] / total_macros
            carbs_ratio = latest_data['carbs'] / total_macros
            
            # Ideal ratios (approximate)
            ideal_protein = 0.25  # 25%
            ideal_fat = 0.30      # 30%
            ideal_carbs = 0.45    # 45%
            
            balance_score = 100 - (
                abs(protein_ratio - ideal_protein) * 100 +
                abs(fat_ratio - ideal_fat) * 100 +
                abs(carbs_ratio - ideal_carbs) * 100
            )
            
            return {
                'balance_score': max(0, balance_score),
                'current_ratios': {
                    'protein': protein_ratio,
                    'fat': fat_ratio,
                    'carbs': carbs_ratio
                },
                'recommendations': self._get_balance_recommendations(protein_ratio, fat_ratio, carbs_ratio)
            }
        
        return {'balance_score': 0, 'recommendations': ['Insufficient data for analysis']}
    
    def _create_visualizations(self, df, user):
        """Create matplotlib visualizations"""
        visualizations = {}
        
        try:
            # 1. Nutrition Trends Over Time
            plt.figure(figsize=(12, 8))
            
            plt.subplot(2, 2, 1)
            plt.plot(df['week'], df['calories'], marker='o', label='Calories')
            plt.title('Calorie Intake Trend')
            plt.xlabel('Week')
            plt.ylabel('Calories')
            plt.grid(True, alpha=0.3)
            
            plt.subplot(2, 2, 2)
            plt.plot(df['week'], df['protein'], marker='s', color='orange', label='Protein')
            plt.title('Protein Intake Trend')
            plt.xlabel('Week')
            plt.ylabel('Protein (g)')
            plt.grid(True, alpha=0.3)
            
            plt.subplot(2, 2, 3)
            plt.plot(df['week'], df['fat'], marker='^', color='red', label='Fat')
            plt.title('Fat Intake Trend')
            plt.xlabel('Week')
            plt.ylabel('Fat (g)')
            plt.grid(True, alpha=0.3)
            
            plt.subplot(2, 2, 4)
            plt.plot(df['week'], df['carbs'], marker='d', color='green', label='Carbs')
            plt.title('Carbohydrate Intake Trend')
            plt.xlabel('Week')
            plt.ylabel('Carbs (g)')
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Save to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            trends_chart = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            visualizations['trends_chart'] = trends_chart
            
            # 2. Nutrition Balance Pie Chart
            latest_data = df.iloc[-1]
            labels = ['Protein', 'Fat', 'Carbs']
            sizes = [latest_data['protein'], latest_data['fat'], latest_data['carbs']]
            colors = ['#ff9999', '#66b3ff', '#99ff99']
            
            plt.figure(figsize=(8, 6))
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.title('Current Macronutrient Distribution')
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            balance_chart = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            visualizations['balance_chart'] = balance_chart
            
            # 3. Goal Achievement Trend
            plt.figure(figsize=(10, 6))
            plt.plot(df['week'], df['goal_achievement'] * 100, marker='o', linewidth=2, markersize=8)
            plt.axhline(y=80, color='r', linestyle='--', alpha=0.7, label='Target (80%)')
            plt.title('Goal Achievement Rate Over Time')
            plt.xlabel('Week')
            plt.ylabel('Achievement Rate (%)')
            plt.ylim(0, 100)
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            achievement_chart = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            visualizations['achievement_chart'] = achievement_chart
            
        except Exception as e:
            logger.error(f"Visualization creation failed: {e}")
            visualizations['error'] = str(e)
        
        return visualizations
    
    def _get_important_factors(self, model, feature_names):
        """Get most important factors from logistic regression"""
        coefficients = model.coef_[0]
        importance = [(feature_names[i], abs(coefficients[i])) for i in range(len(feature_names))]
        importance.sort(key=lambda x: x[1], reverse=True)
        return [factor[0] for factor in importance[:2]]
    
    def _get_balance_recommendations(self, protein_ratio, fat_ratio, carbs_ratio):
        """Generate nutrition balance recommendations"""
        recommendations = []
        
        if protein_ratio < 0.20:
            recommendations.append("Increase protein intake with lean meats, eggs, or legumes")
        elif protein_ratio > 0.35:
            recommendations.append("Consider reducing protein and balancing with healthy carbs")
        
        if fat_ratio < 0.25:
            recommendations.append("Add healthy fats like avocados, nuts, or olive oil")
        elif fat_ratio > 0.40:
            recommendations.append("Reduce fat intake and focus on lean proteins and complex carbs")
        
        if carbs_ratio < 0.35:
            recommendations.append("Include more complex carbohydrates like whole grains and vegetables")
        elif carbs_ratio > 0.55:
            recommendations.append("Reduce simple carbs and increase protein and healthy fats")
        
        if not recommendations:
            recommendations.append("Your macronutrient balance looks good! Keep it up!")
        
        return recommendations
    
    def _generate_basic_insights(self, user):
        """Generate basic insights when no historical data is available"""
        from .models import DietaryGoal, ScanHistory
        
        dietary_goals = DietaryGoal.objects.filter(user=user).first()
        recent_scans = ScanHistory.objects.filter(user=user).count()
        
        insights = {
            'basic_analysis': True,
            'first_time_user': True,
            'recommendations': []
        }
        
        if dietary_goals:
            # Calculate current progress
            calories_progress = (dietary_goals.calories_consumed / dietary_goals.calories_target * 100) if dietary_goals.calories_target > 0 else 0
            protein_progress = (dietary_goals.protein_consumed / dietary_goals.protein_target * 100) if dietary_goals.protein_target > 0 else 0
            
            insights['current_progress'] = {
                'calories': calories_progress,
                'protein': protein_progress
            }
            
            # Provide immediate value based on current goals
            if dietary_goals.calories_target > 0:
                insights['recommendations'].append(f"Your daily calorie target is {dietary_goals.calories_target}. Great starting point!")
            
            if dietary_goals.protein_target > 0:
                insights['recommendations'].append(f"Aim for {dietary_goals.protein_target}g of protein daily for optimal health.")
        
        # Add beginner-friendly tips
        insights['recommendations'].extend([
            "Welcome to your nutrition journey! Start by scanning your meals regularly.",
            "Focus on eating a variety of colorful fruits and vegetables.",
            "Stay hydrated and aim for balanced meals with protein, healthy fats, and complex carbs.",
            "Consistency is key - small daily improvements lead to lasting results!",
            "Track your favorite healthy foods to build good habits."
        ])
        
        if recent_scans == 0:
            insights['recommendations'].insert(0, "Start by scanning your first food item to begin your nutrition analysis!")
        elif recent_scans < 3:
            insights['recommendations'].insert(0, f"Great start with {recent_scans} scans! Keep going to unlock more insights.")
        
        return insights
    
    def _generate_enhanced_basic_insights(self, user, logs):
        """Generate enhanced insights for users with 1-2 weeks of data"""
        from .models import DietaryGoal, ScanHistory
        
        dietary_goals = DietaryGoal.objects.filter(user=user).first()
        recent_scans = ScanHistory.objects.filter(user=user).count()
        
        insights = {
            'basic_analysis': True,
            'data_weeks': logs.count(),
            'recommendations': []
        }
        
        if dietary_goals:
            # Calculate current progress
            calories_progress = (dietary_goals.calories_consumed / dietary_goals.calories_target * 100) if dietary_goals.calories_target > 0 else 0
            protein_progress = (dietary_goals.protein_consumed / dietary_goals.protein_target * 100) if dietary_goals.protein_target > 0 else 0
            
            insights['current_progress'] = {
                'calories': calories_progress,
                'protein': protein_progress
            }
            
            # Generate personalized recommendations based on available data
            if calories_progress < 80:
                insights['recommendations'].append("You're doing great with calorie control! Consider adding more nutrient-dense foods.")
            elif calories_progress > 120:
                insights['recommendations'].append("Consider portion control and focus on high-fiber foods to feel fuller.")
            else:
                insights['recommendations'].append("Your calorie intake is well-balanced!")
            
            if protein_progress < 80:
                insights['recommendations'].append("Try to include more protein sources like lean meats, eggs, or legumes.")
            elif protein_progress > 120:
                insights['recommendations'].append("Great protein intake! Make sure to balance with healthy carbs and fats.")
            else:
                insights['recommendations'].append("Excellent protein balance!")
        
        # Add general tips based on scan activity
        if recent_scans < 5:
            insights['recommendations'].append("Keep scanning foods regularly to build better nutrition insights!")
        elif recent_scans < 15:
            insights['recommendations'].append("Good scanning habits! Try to scan a variety of foods for better analysis.")
        else:
            insights['recommendations'].append("Excellent tracking consistency! Your data will provide great insights.")
        
        # Add motivational insights
        insights['recommendations'].extend([
            "Every scan helps build a better picture of your nutrition patterns.",
            "Focus on whole foods and balanced meals for optimal health.",
            "Small consistent changes lead to big results over time!"
        ])
        
        return insights

# Helper function for views
def get_ml_insights(user):
    """Get ML insights for a user"""
    analyzer = NutritionMLAnalyzer()
    return analyzer.analyze_nutrition_trends(user)
