# main/templatetags/time_filters.py
from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def time_remaining(timedelta_obj):
    """Convert timedelta to human readable remaining time"""
    if not timedelta_obj:
        return "No time set"
    
    total_seconds = int(timedelta_obj.total_seconds())
    
    if total_seconds <= 0:
        return "Time expired"
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 and days == 0:  # Only show minutes if less than a day
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    
    if not parts:
        return "Less than a minute"
    
    return ", ".join(parts)

@register.filter
def format_timedelta(timedelta_obj):
    """Format timedelta for display"""
    if not timedelta_obj:
        return ""
    
    # Convert to datetime by adding to current time
    now = timezone.now()
    future_time = now + timedelta_obj
    return future_time