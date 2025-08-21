# AI-Powered Personalized Tips Generation
import openai
import os
from django.conf import settings
from .models import PersonalizedTip
import logging

logger = logging.getLogger(__name__)

class AITipsGenerator:
    def __init__(self):
        # Initialize OpenAI client (you'll need to add OPENAI_API_KEY to settings)
        self.client = None
        if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai
    
    def generate_personalized_tips(self, user, dietary_goals, progress_data, activity_data):
        """Generate AI-powered personalized nutrition tips"""
        try:
            if not self.client:
                # Fallback to rule-based tips if AI is not available
                return self._generate_rule_based_tips(user, dietary_goals, progress_data, activity_data)
            
            # Prepare context for AI
            context = self._prepare_user_context(user, dietary_goals, progress_data, activity_data)
            
            # Generate tips using OpenAI
            response = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a nutrition expert providing personalized health tips. Generate 3-5 actionable, specific tips based on the user's data. Each tip should be concise (max 100 characters) and actionable."
                    },
                    {
                        "role": "user",
                        "content": f"Based on this user's nutrition data: {context}, provide personalized nutrition tips."
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            tips_text = response.choices[0].message.content
            tips = self._parse_ai_tips(tips_text)
            
            return self._save_tips_to_db(user, tips)
            
        except Exception as e:
            logger.error(f"AI tips generation failed: {e}")
            # Fallback to rule-based tips
            return self._generate_rule_based_tips(user, dietary_goals, progress_data, activity_data)
    
    def _prepare_user_context(self, user, dietary_goals, progress_data, activity_data):
        """Prepare user context for AI analysis"""
        context = {
            'calories_progress': progress_data.get('calories_progress', 0),
            'protein_progress': progress_data.get('protein_progress', 0),
            'fat_progress': progress_data.get('fat_progress', 0),
            'carbs_progress': progress_data.get('carbs_progress', 0),
            'recent_scans': activity_data.get('recent_scans_count', 0),
            'days_active': activity_data.get('days_active', 0),
            'goals': {
                'calories': dietary_goals.calories_target,
                'protein': dietary_goals.protein_target,
                'fat': dietary_goals.fat_target,
                'carbs': dietary_goals.carbs_target
            }
        }
        return context
    
    def _parse_ai_tips(self, tips_text):
        """Parse AI-generated tips into structured format"""
        tips = []
        lines = tips_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                # Clean up the tip text
                tip = line.lstrip('-•0123456789. ').strip()
                if len(tip) > 20:  # Ensure it's a meaningful tip
                    tips.append({
                        'text': tip,
                        'tip_type': self._categorize_tip(tip),
                        'priority': len(tips) + 1
                    })
        
        return tips[:5]  # Limit to 5 tips
    
    def _categorize_tip(self, tip_text):
        """Categorize tip based on content"""
        tip_lower = tip_text.lower()
        
        if any(word in tip_lower for word in ['urgent', 'critical', 'important', 'must']):
            return 'critical'
        elif any(word in tip_lower for word in ['warning', 'careful', 'watch', 'limit']):
            return 'warning'
        elif any(word in tip_lower for word in ['great', 'excellent', 'good', 'well done']):
            return 'success'
        else:
            return 'info'
    
    def _generate_rule_based_tips(self, user, dietary_goals, progress_data, activity_data):
        """Generate rule-based tips as fallback"""
        tips = []
        
        calories_progress = progress_data.get('calories_progress', 0)
        protein_progress = progress_data.get('protein_progress', 0)
        recent_scans = activity_data.get('recent_scans_count', 0)
        
        # Calorie-based tips
        if calories_progress < 50:
            tips.append({
                'text': 'You\'re under your calorie goal. Consider adding healthy snacks like nuts or fruits.',
                'tip_type': 'warning',
                'priority': 1
            })
        elif calories_progress > 90:
            tips.append({
                'text': 'You\'re close to your calorie limit. Focus on low-calorie, nutrient-dense foods.',
                'tip_type': 'critical',
                'priority': 1
            })
        
        # Protein-based tips
        if protein_progress < 60:
            tips.append({
                'text': 'Boost your protein intake with lean meats, eggs, or legumes.',
                'tip_type': 'info',
                'priority': 2
            })
        
        # Activity-based tips
        if recent_scans < 3:
            tips.append({
                'text': 'Try scanning more products to better track your nutrition this week.',
                'tip_type': 'info',
                'priority': 3
            })
        elif recent_scans > 10:
            tips.append({
                'text': 'Great job staying active with food tracking! Keep it up!',
                'tip_type': 'success',
                'priority': 1
            })
        
        # General health tips
        tips.append({
            'text': 'Remember to stay hydrated - aim for 8 glasses of water daily.',
            'tip_type': 'info',
            'priority': 4
        })
        
        return self._save_tips_to_db(user, tips[:5])
    
    def _save_tips_to_db(self, user, tips):
        """Save generated tips to database"""
        saved_tips = []
        
        for tip_data in tips:
            tip = PersonalizedTip.objects.create(
                user=user,
                message=tip_data['text'],
                tip_type=tip_data['tip_type'],
                priority=tip_data['priority']
            )
            saved_tips.append(tip)
        
        return saved_tips

# Helper function to integrate with existing views
def get_ai_personalized_tips(user, dietary_goals, progress_data, activity_data):
    """Get AI-generated personalized tips for a user"""
    generator = AITipsGenerator()
    return generator.generate_personalized_tips(user, dietary_goals, progress_data, activity_data)
