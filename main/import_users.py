import csv
import os
import django
import re

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voting_software.settings')
django.setup()

from django.contrib.auth.models import User

csv_path = r'C:\Users\Ernest Mpiani\Downloads\nss.csv'

def clean_nss_number(nss_number):
    """Clean NSS number by removing spaces, dots, and commas"""
    if not nss_number:
        return None
    # Remove spaces, dots, commas, and any other special characters
    cleaned = re.sub(r'[\s.,-]+', '', str(nss_number).strip())
    return cleaned

def clean_email(email):
    """Clean email address"""
    if not email:
        return None
    # Remove spaces and convert to lowercase
    cleaned = str(email).strip().lower()
    # Fix common iCloud email issue (remove space before @)
    cleaned = cleaned.replace(' @', '@')
    cleaned = cleaned.replace('@ ', '@')
    # Remove any other whitespace
    cleaned = ' '.join(cleaned.split())
    return cleaned

def clean_name(name):
    """Clean name by removing extra spaces"""
    if not name:
        return None
    return ' '.join(str(name).strip().split())

try:
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Track duplicates and errors
        created_count = 0
        skipped_count = 0
        error_count = 0
        duplicate_emails = {}
        duplicate_nss = {}
        
        print("=" * 60)
        print("IMPORTING NSS USERS")
        print("=" * 60)
        
        for row_num, row in enumerate(reader, start=2):  # start=2 for row numbers (1-based with header)
            try:
                # Get and clean data
                raw_name = row.get('Name ', '') or row.get('Name', '')  # Handle space in column name
                raw_email = row.get('Email', '')
                raw_nss = row.get('NSS number', '')
                
                # Clean the data
                name = clean_name(raw_name)
                email = clean_email(raw_email)
                nss_number = clean_nss_number(raw_nss)
                
                # Skip rows with missing essential data
                if not name or not email or not nss_number:
                    print(f"⚠️  Row {row_num}: Skipped - Missing required data")
                    print(f"   Name: '{raw_name}', Email: '{raw_email}', NSS: '{raw_nss}'")
                    skipped_count += 1
                    continue
                
                # Check for duplicate NSS numbers in this import session
                if nss_number in duplicate_nss:
                    print(f"⚠️  Row {row_num}: Duplicate NSS number found - {nss_number}")
                    print(f"   First seen at row {duplicate_nss[nss_number]}")
                    print(f"   Name: {name}")
                    error_count += 1
                    continue
                else:
                    duplicate_nss[nss_number] = row_num
                
                # Check for duplicate emails in this import session
                if email in duplicate_emails:
                    print(f"⚠️  Row {row_num}: Duplicate email found - {email}")
                    print(f"   First seen at row {duplicate_emails[email]}")
                    print(f"   Name: {name}")
                    error_count += 1
                    continue
                else:
                    duplicate_emails[email] = row_num
                
                # Split name: first word is first name, rest is last name
                name_parts = name.split()
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                
                # Check if user already exists by username (NSS number)
                if User.objects.filter(username=nss_number).exists():
                    print(f"⏭️  Row {row_num}: User already exists (NSS: {nss_number})")
                    print(f"   Name: {first_name} {last_name}")
                    skipped_count += 1
                    continue
                
                # Check if email already exists (optional - to prevent duplicate emails)
                if User.objects.filter(email=email).exists():
                    existing_user = User.objects.get(email=email)
                    print(f"⚠️  Row {row_num}: Email already in use - {email}")
                    print(f"   Existing user: {existing_user.username} - {existing_user.get_full_name()}")
                    print(f"   New user: {first_name} {last_name} (NSS: {nss_number})")
                    
                    # Ask what to do (optional - you can remove this for automated imports)
                    # For now, we'll skip
                    print(f"   Skipping to avoid duplicate email")
                    error_count += 1
                    continue
                
                # Create user
                user = User.objects.create_user(
                    username=nss_number,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password='defaultpassword123'  # Same default password
                )
                
                created_count += 1
                print(f"✅ Row {row_num}: Created user - {nss_number}")
                print(f"   Name: {first_name} {last_name}")
                print(f"   Email: {email}")
                print(f"   Username: {nss_number}")
                print()
                
            except Exception as e:
                print(f"❌ Row {row_num}: Error - {str(e)}")
                print(f"   Raw data: {row}")
                error_count += 1
        
        # Print summary
        print("=" * 60)
        print("IMPORT SUMMARY")
        print("=" * 60)
        print(f"✅ Users created: {created_count}")
        print(f"⏭️  Users skipped (already exist): {skipped_count}")
        print(f"❌ Errors: {error_count}")
        print(f"📊 Total rows processed: {row_num}")
        print("=" * 60)
        
except FileNotFoundError:
    print(f"❌ File not found: {csv_path}")
    print("Please check the file path and try again.")
except Exception as e:
    print(f"❌ Unexpected error: {str(e)}")