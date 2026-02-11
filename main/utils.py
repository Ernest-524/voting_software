# main/utils.py
import os
import csv
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def extract_names_from_full_name(full_name):
    """
    Extract first name and last name from a full name.
    Handles cases like: 'John Doe', 'John Michael Doe', 'John', etc.
    """
    names = full_name.strip().split()
    
    if len(names) == 0:
        return "User", "Voter"
    elif len(names) == 1:
        return names[0], "Voter"
    elif len(names) == 2:
        return names[0], names[1]
    else:
        # For 3+ names: first name is first word, last name is last word
        return names[0], names[-1]

def generate_unique_password(username, phone_number=None):
    """
    Generate a unique password based on username and phone number.
    You can customize this pattern as needed.
    """
    # Example pattern: First 3 letters of username + last 4 digits of phone (if available)
    if phone_number and len(phone_number) >= 4:
        last_digits = phone_number[-4:]
    else:
        # Generate random 4 digits if no phone
        import random
        last_digits = str(random.randint(1000, 9999))
    
    # Take first 3 characters of username (uppercase)
    username_part = username[:3].upper()
    
    # Create password: username_part + last_digits + special char
    password = f"{username_part}{last_digits}@Vote"
    
    return password

def send_user_credentials(user, password):
    """
    Send email with login credentials to a user.
    """
    subject = 'Your Voting System Login Credentials'
    
    # HTML email template
    html_message = render_to_string('main/email/credentials_email.html', {
        'user': user,
        'password': password,
        'site_name': 'Election Voting System',
    })
    
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

def send_credentials_to_all_users(request):
    """
    Send credentials to all existing users.
    This will be called from a view when a button is clicked.
    """
    results = {
        'success': [],
        'failed': []
    }
    
    users = User.objects.all()
    total_users = users.count()
    
    for user in users:
        # Generate or retrieve password
        # For now, we'll generate new passwords for all users
        # In reality, you might want to store passwords or generate consistent ones
        
        # Generate password based on username
        password = generate_unique_password(user.username)
        
        # Set the password
        user.set_password(password)
        user.save()
        
        # Send email
        success, message = send_user_credentials(user, password)
        
        if success:
            results['success'].append({
                'user': user.username,
                'email': user.email,
                'password': password
            })
        else:
            results['failed'].append({
                'user': user.username,
                'email': user.email,
                'error': message
            })
    
    return results, total_users