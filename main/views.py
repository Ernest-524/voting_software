from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .models import Position, Candidate, Vote, ElectionSettings
from .forms import PositionForm, CandidateForm, VotingForm, CustomLoginForm, ElectionSettingsForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
import datetime
from io import BytesIO
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib.admin.views.decorators import staff_member_required
from .utils import send_credentials_to_all_users
import time
from django.views.decorators.csrf import csrf_protect
from django.middleware.csrf import get_token



# Create your views here.
def user_homepage(request):
    return render(request, 'main/user_home.html')

# In views.py - update admin_homepage function
# In views.py
def admin_homepage(request):
    from django.utils import timezone  # IMPORT HERE
    
    # Get or create election settings
    election_settings = ElectionSettings.objects.first()
    if not election_settings:
        election_settings = ElectionSettings.objects.create(election_name="General Election")
    
    # Get statistics
    total_voters = User.objects.count()
    voted_count = Vote.objects.values('voter').distinct().count()
    not_voted_count = total_voters - voted_count
    positions_count = Position.objects.count()
    candidates_count = Candidate.objects.count()
    
    return render(request, 'main/admin_home.html', {
        'election_settings': election_settings,
        'total_voters': total_voters,
        'voted_count': voted_count,
        'not_voted_count': not_voted_count,
        'positions_count': positions_count,
        'candidates_count': candidates_count,
        'timezone': timezone,  # ADD THIS LINE
    })

def logout_view(request):
    logout(request)
    return redirect('login')

def manage_positions(request):
    positions = Position.objects.all()
    return render(request, 'main/manage_positions.html', {'positions': positions})

def register_position(request):
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            position_name = form.cleaned_data.get('position_name')
            messages.success(request, f"Position ({position_name}) created successfully!")
            form.save()
            return redirect('manage_positions')
    else:
        form = PositionForm()
    return render(request, 'main/register_position.html', {'form': form})

def manage_candidates(request):
    positions = Position.objects.prefetch_related('candidate_position').all()
    return render(request, 'main/manage_candidates.html', {'positions': positions})

def register_candidate(request):
    if request.method == 'POST':
        form = CandidateForm(request.POST, request.FILES)
        if form.is_valid():
            candidate_name = form.cleaned_data.get('candidate_name')
            candidate_position = form.cleaned_data.get('candidate_position')
            if Candidate.objects.filter(candidate_name=candidate_name, candidate_position=candidate_position).exists():
                messages.error(request, f"Candidate ({candidate_name}) is already registered for the position ({candidate_position}).")
            else:
                form.save()
                messages.success(request, f"Candidate ({candidate_name}) registered successfully for the position ({candidate_position}).")
                return redirect('manage_candidates')
    else:
        form = CandidateForm()
    return render(request, 'main/register_candidate.html', {'form': form})

@login_required
def vote_view(request):
    try:
        # For now, allow voting regardless of election settings
        # We'll fix this after we get voting working
        is_election_active = True  # TEMPORARY: Always allow voting
        
        if not is_election_active:
            messages.error(request, "Voting is not currently active.")
            return redirect('user_homepage')
        
        positions = Position.objects.prefetch_related('candidate_position').all()

        # Check if user has already voted
        has_voted = Vote.objects.filter(voter=request.user).exists()
        if has_voted:
            messages.error(request, "You have already voted. Voting is allowed only once.")
            return redirect('user_homepage')
        
        # ADD THIS LINE: Get election settings for template
        election_settings = ElectionSettings.objects.first()
        
        if request.method == 'POST':
            form = VotingForm(request.POST, positions=positions)
            if form.is_valid():
                for position in positions:
                    candidates = position.candidate_position.all()
                    
                    if candidates.count() > 1:
                        # Multiple candidates - get selected candidate ID
                        selected_candidate_id = form.cleaned_data.get(f'position_{position.id}')
                        if selected_candidate_id:
                            selected_candidate = Candidate.objects.get(id=int(selected_candidate_id))
                            Vote.objects.create(
                                voter=request.user,
                                position=position,
                                candidate=selected_candidate,
                                vote_type=Vote.MULTIPLE_CANDIDATES,
                                choice='selected'
                            )
                    else:
                        # Single candidate - create yes/no vote
                        for candidate in candidates:
                            choice = form.cleaned_data.get(f'candidate_{candidate.id}')
                            if choice:
                                Vote.objects.create(
                                    voter=request.user,
                                    position=position,
                                    candidate=candidate,
                                    vote_type=Vote.SINGLE_CANDIDATE,
                                    choice=choice
                                )
                
                messages.success(request, "Your votes have been submitted!")
                return redirect('user_homepage')
            else:
                messages.error(request, "There was an error with your vote submission. Please complete all required fields.")
        else:
            form = VotingForm(positions=positions)
        
        # UPDATED: Add election_settings to context
        return render(request, 'main/vote.html', {
            'form': form,
            'positions': positions,
            'voting_closed': False,
            'is_election_active': is_election_active,
            'election_settings': election_settings  # ADDED THIS LINE
        })
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('user_homepage')
    
@login_required
def manage_election(request):
    """
    Admin page to configure election timing
    """
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Access denied. Admin only.")
        return redirect('user_homepage')
    
    # Get or create election settings
    election_settings = ElectionSettings.objects.first()
    if not election_settings:
        election_settings = ElectionSettings.objects.create(election_name="General Election")
    
    if request.method == 'POST':
        form = ElectionSettingsForm(request.POST, instance=election_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Election settings updated successfully!")
            return redirect('manage_election')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ElectionSettingsForm(instance=election_settings)
    
    return render(request, 'main/manage_election.html', {
        'form': form,
        'election_settings': election_settings,
        'now': timezone.now(),
    })

@login_required
def start_election_manual(request):
    """
    Start election immediately with manual override
    """
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Access denied.")
        return redirect('user_homepage')
    
    election_settings = ElectionSettings.objects.first()
    if not election_settings:
        election_settings = ElectionSettings.objects.create(election_name="General Election")
    
    # Use the model method
    election_settings.start_manually()
    
    messages.success(request, "✅ Election started manually! Manual override is now ACTIVE.")
    return redirect('manage_election')

@login_required
def stop_election_manual(request):
    """
    Stop election immediately with manual override
    """
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Access denied.")
        return redirect('user_homepage')
    
    election_settings = ElectionSettings.objects.first()
    if not election_settings:
        election_settings = ElectionSettings.objects.create(election_name="General Election")
    
    # Use the model method
    election_settings.stop_manually()
    
    messages.success(request, "⛔ Election stopped manually! Manual override is now ACTIVE.")
    return redirect('manage_election')

# ... ALL YOUR OTHER EXISTING VIEW FUNCTIONS STAY THE SAME ...
# (user_homepage, admin_homepage, logout_view, manage_positions, etc.)

def manage_vote_dashboard(request):
    total_voters = User.objects.count()
    voted_count = Vote.objects.values('voter').distinct().count()
    not_voted_count = total_voters - voted_count
    return render(request, 'main/manage_vote_dashboard.html', {
        'total_voters': total_voters,
        'voted_count': voted_count,
        'not_voted_count': not_voted_count
    })

def voter_list(request):
    voters = User.objects.all()
    return render(request, 'main/voter_list.html', {'voters': voters})

def voted_list(request):
    voted_user_ids = Vote.objects.values_list('voter', flat=True).distinct()
    voted_users = User.objects.filter(id__in=voted_user_ids)
    votes = Vote.objects.select_related('voter', 'candidate', 'position')
    user_votes = {}
    for user in voted_users:
        user_votes[user.id] = list(votes.filter(voter=user))
    return render(request, 'main/voted_list.html', {
        'voted_users': voted_users,
        'user_votes': user_votes,
    })

def vote_results(request):
    positions = Position.objects.prefetch_related('candidate_position')
    results = []
    
    for position in positions:
        candidates = position.candidate_position.all()
        candidate_data = []
        
        for candidate in candidates:
            if position.has_multiple_candidates():
                # For multiple candidates, count "selected" votes
                selected_count = Vote.objects.filter(
                    position=position, 
                    candidate=candidate, 
                    vote_type=Vote.MULTIPLE_CANDIDATES
                ).count()
                
                # Total votes for this position (each voter votes once)
                total_votes_position = Vote.objects.filter(position=position).values('voter').distinct().count()
                
                candidate_data.append({
                    'candidate': candidate,
                    'selected_count': selected_count,
                    'total_votes': total_votes_position,
                    'is_multiple': True,
                })
            else:
                # For single candidate, count yes/no votes
                yes_count = Vote.objects.filter(
                    position=position, 
                    candidate=candidate, 
                    choice='yes',
                    vote_type=Vote.SINGLE_CANDIDATE
                ).count()
                
                no_count = Vote.objects.filter(
                    position=position, 
                    candidate=candidate, 
                    choice='no',
                    vote_type=Vote.SINGLE_CANDIDATE
                ).count()
                
                total = yes_count + no_count
                yes_pct = int((yes_count / total) * 100) if total > 0 else 0
                yes_style = f"width: {yes_pct}%;"
                
                candidate_data.append({
                    'candidate': candidate,
                    'yes_count': yes_count,
                    'no_count': no_count,
                    'total': total,
                    'yes_pct': yes_pct,
                    'yes_style': yes_style,
                    'is_multiple': False,
                })
        
        results.append({
            'position': position,
            'candidates': candidate_data,
            'has_multiple': position.has_multiple_candidates(),
        })
    
    return render(request, 'main/vote_results.html', {'results': results})

def not_voted_list(request):
    voted_user_ids = Vote.objects.values_list('voter', flat=True).distinct()
    not_voted_users = User.objects.exclude(id__in=voted_user_ids)
    return render(request, 'main/not_voted_list.html', {'not_voted_users': not_voted_users})

def candidate_voters(request, candidate_id):
    candidate = Candidate.objects.get(id=candidate_id)
    votes = Vote.objects.filter(candidate=candidate).select_related('voter', 'position')
    voters = [vote.voter for vote in votes]
    return render(request, 'main/candidate_voters.html', {
        'candidate': candidate,
        'votes': votes,
        'voters': voters,
    })

@csrf_protect
class CustomLoginView(LoginView):
    template_name = 'main/login.html'

    def get_success_url(self):
        if self.request.user.is_superuser or self.request.user.is_staff:
            return reverse_lazy('admin_homepage')
        else:
            return reverse_lazy('user_homepage')

def export_vote_results_pdf(request):
    """
    Generate a PDF summarising:
    - total voters
    - number who voted
    - number not voted
    - per-position candidate counts
    """
    # basic counts
    total_voters = User.objects.count()
    voted_count = Vote.objects.values('voter').distinct().count()
    not_voted_count = total_voters - voted_count

    # build results same as vote_results view
    positions = Position.objects.prefetch_related('candidate_position').all()
    results = []
    
    for position in positions:
        candidates = position.candidate_position.all()
        candidate_rows = []
        
        for candidate in candidates:
            if position.has_multiple_candidates():
                selected_count = Vote.objects.filter(
                    position=position, 
                    candidate=candidate, 
                    vote_type=Vote.MULTIPLE_CANDIDATES
                ).count()
                
                total_votes_position = Vote.objects.filter(position=position).values('voter').distinct().count()
                percentage = (selected_count / total_votes_position * 100) if total_votes_position > 0 else 0
                
                candidate_rows.append({
                    'name': f"{candidate.candidate_name.first_name} {candidate.candidate_name.last_name}",
                    'selected': selected_count,
                    'total_votes': total_votes_position,
                    'percentage': f"{percentage:.1f}%",
                    'is_multiple': True,
                })
            else:
                yes_count = Vote.objects.filter(
                    position=position, 
                    candidate=candidate, 
                    choice='yes',
                    vote_type=Vote.SINGLE_CANDIDATE
                ).count()
                
                no_count = Vote.objects.filter(
                    position=position, 
                    candidate=candidate, 
                    choice='no',
                    vote_type=Vote.SINGLE_CANDIDATE
                ).count()
                
                total = yes_count + no_count
                yes_percentage = (yes_count / total * 100) if total > 0 else 0
                
                candidate_rows.append({
                    'name': f"{candidate.candidate_name.first_name} {candidate.candidate_name.last_name}",
                    'yes': yes_count,
                    'no': no_count,
                    'total': total,
                    'yes_percentage': f"{yes_percentage:.1f}%",
                    'is_multiple': False,
                })
        
        results.append({
            'position': position.position_name,
            'has_multiple': position.has_multiple_candidates(),
            'candidates': candidate_rows
        })

    # build PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Vote Results", styles['Title']))
    story.append(Spacer(1, 12))

    # summary counts
    story.append(Paragraph(f"Total registered voters: <b>{total_voters}</b>", styles['Normal']))
    story.append(Paragraph(f"Voted: <b>{voted_count}</b>", styles['Normal']))
    story.append(Paragraph(f"Yet to vote: <b>{not_voted_count}</b>", styles['Normal']))
    story.append(Spacer(1, 12))

    # per-position tables
    for r in results:
        story.append(Paragraph(r['position'], styles['Heading2']))
        story.append(Spacer(1, 6))

        if r['has_multiple']:
            # Table for multiple candidates
            data = [["Candidate", "Votes", "Total Votes", "Percentage"]]
            for c in r['candidates']:
                data.append([c['name'], str(c['selected']), str(c['total_votes']), c['percentage']])
            
            table = Table(data, colWidths=[200, 60, 80, 80])
        else:
            # Table for single candidate
            data = [["Candidate", "Yes", "No", "Total", "Yes %"]]
            for c in r['candidates']:
                data.append([c['name'], str(c['yes']), str(c['no']), str(c['total']), c['yes_percentage']])
            
            table = Table(data, colWidths=[200, 60, 60, 60, 60])

        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#3E2723")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('ALIGN',(1,1),(-1,-1),'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="vote_results.pdf"'
    return response

@staff_member_required
def send_credentials_view(request):
    """
    Admin view to send credentials to all users
    """
    if not (request.user.is_superuser or request.user.is_staff):
        messages.error(request, "Access denied. Admin only.")
        return redirect('user_homepage')
    
    if request.method == 'POST':
        # Get total users
        total_users = User.objects.count()
        
        try:
            # Import your send_credentials_to_all_users function
            from .utils import send_credentials_to_all_users
            
            # Send credentials
            results, total = send_credentials_to_all_users(request)
            
            success_count = len(results['success'])
            failed_count = len(results['failed'])
            
            messages.success(request, 
                f"✅ Credentials sent to {success_count} out of {total} users. "
                f"Failed: {failed_count}.")
            
            # Store for display
            request.session['email_results'] = {
                'success_count': success_count,
                'failed_count': failed_count,
                'total_users': total
            }
            
        except Exception as e:
            messages.error(request, f"❌ Error sending emails: {str(e)}")
        
        return redirect('send_credentials')
    
    # GET request - show the page
    results = request.session.pop('email_results', None)
    total_users = User.objects.count()
    
    return render(request, 'main/send_credentials.html', {
        'results': results,
        'total_users': total_users,
    })

@staff_member_required
def test_email_view(request):
    """Send a test email to admin"""
    try:
        send_mail(
            'Test Email from Voting System',
            'This is a test email to verify email configuration is working.',
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
        messages.success(request, f"Test email sent successfully to {request.user.email}")
    except Exception as e:
        messages.error(request, f"Failed to send test email: {str(e)}")
    
    return redirect('send_credentials')

from django.http import HttpResponse
from django.conf import settings
import sys
import os

def csrf_test(request):
    response = f"""
    <html>
    <body>
        <h1>CSRF Settings Debug</h1>
        <h2>CSRF_TRUSTED_ORIGINS:</h2>
        <pre>{settings.CSRF_TRUSTED_ORIGINS}</pre>
        
        <h2>ALLOWED_HOSTS:</h2>
        <pre>{settings.ALLOWED_HOSTS}</pre>
        
        <h2>Middleware:</h2>
        <pre>{settings.MIDDLEWARE}</pre>
        
        <h2>Debug Mode:</h2>
        <pre>{settings.DEBUG}</pre>
        
        <h2>Settings Module:</h2>
        <pre>{settings.SETTINGS_MODULE}</pre>
        
        <h2>Environment Variables:</h2>
        <pre>{dict(sorted(dict(os.environ).items()))}</pre>
        
        <h2>Request Headers:</h2>
        <pre>{dict(request.headers)}</pre>
    </body>
    </html>
    """
    return HttpResponse(response)