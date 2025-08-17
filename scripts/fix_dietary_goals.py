#!/usr/bin/env python
"""
Script to fix existing DietaryGoal records and ensure they have all required fields
Run this script after migration to fix any existing records
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/path/to/your/project')  # Update this path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodfacts.settings')

django.setup()

from accounts.models import DietaryGoal
from django.utils import timezone

def fix_dietary_goals():
    """Fix existing DietaryGoal records"""
    print("Fixing existing DietaryGoal records...")
    
    goals = DietaryGoal.objects.all()
    fixed_count = 0
    
    for goal in goals:
        updated = False
        
        # Add missing fields with defaults
        if not hasattr(goal, 'sugar_target') or goal.sugar_target is None:
            goal.sugar_target = 50
            updated = True
        
        if not hasattr(goal, 'sodium_target') or goal.sodium_target is None:
            goal.sodium_target = 2300
            updated = True
            
        if not hasattr(goal, 'fiber_target') or goal.fiber_target is None:
            goal.fiber_target = 25
            updated = True
            
        if not hasattr(goal, 'saturated_fat_target') or goal.saturated_fat_target is None:
            goal.saturated_fat_target = 20
            updated = True
            
        # Add missing consumed fields
        if not hasattr(goal, 'sugar_consumed') or goal.sugar_consumed is None:
            goal.sugar_consumed = 0
            updated = True
            
        if not hasattr(goal, 'sodium_consumed') or goal.sodium_consumed is None:
            goal.sodium_consumed = 0
            updated = True
            
        if not hasattr(goal, 'fiber_consumed') or goal.fiber_consumed is None:
            goal.fiber_consumed = 0
            updated = True
            
        if not hasattr(goal, 'saturated_fat_consumed') or goal.saturated_fat_consumed is None:
            goal.saturated_fat_consumed = 0
            updated = True
            
        if not hasattr(goal, 'last_reset_date') or goal.last_reset_date is None:
            goal.last_reset_date = timezone.now().date()
            updated = True
        
        if updated:
            goal.save()
            fixed_count += 1
            print(f"Fixed DietaryGoal for user: {goal.user.username}")
    
    print(f"Fixed {fixed_count} DietaryGoal records")

if __name__ == '__main__':
    fix_dietary_goals()
