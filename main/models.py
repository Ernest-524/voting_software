from django.db import models
from django.contrib.auth.models import User
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone 

# Create your models here.
class Position(models.Model):
    position_name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.position_name
    
    def has_multiple_candidates(self):
        """Check if this position has more than one candidate"""
        return self.candidate_position.count() > 1

class Candidate(models.Model):
    candidate_name = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidate_name')
    photo = models.ImageField(upload_to='candidate_photos/')
    candidate_position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='candidate_position')

    class Meta:
        unique_together = ('candidate_name', 'candidate_position')

    def __str__(self):
        return f"{self.candidate_name.first_name} {self.candidate_name.last_name}"

class Vote(models.Model):
    # Different vote types based on number of candidates
    SINGLE_CANDIDATE = 'single'
    MULTIPLE_CANDIDATES = 'multiple'
    
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    # For single candidate: 'yes' or 'no'
    # For multiple candidates: 'selected' (if this candidate was chosen)
    vote_type = models.CharField(max_length=20, default=SINGLE_CANDIDATE)
    choice = models.CharField(max_length=10)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Each voter can only vote once per position
        unique_together = ('voter', 'position')

    def __str__(self):
        if self.vote_type == self.SINGLE_CANDIDATE:
            return f"{self.voter.username} voted {self.choice} for {self.candidate} as {self.position}"
        else:
            return f"{self.voter.username} selected {self.candidate} for {self.position}"
    
    def save(self, *args, **kwargs):
        # Determine vote type based on number of candidates
        if self.position.candidate_position.count() > 1:
            self.vote_type = self.MULTIPLE_CANDIDATES
            self.choice = 'selected'
        else:
            self.vote_type = self.SINGLE_CANDIDATE
        super().save(*args, **kwargs)

class ElectionSettings(models.Model):
    """
    Controls when voting is active
    - Can use scheduled timing (automatic)
    - Can use manual override (buttons)
    """
    election_name = models.CharField(max_length=200, default="General Election")
    
    # Manual control
    is_active = models.BooleanField(default=False, 
                                    help_text="Current active status")
    is_manual_override = models.BooleanField(default=False,
                                            help_text="Check to use manual controls instead of schedule")
    
    # Scheduled timing
    scheduled_start = models.DateTimeField(null=True, blank=True,
                                          help_text="When voting should automatically start")
    scheduled_end = models.DateTimeField(null=True, blank=True,
                                        help_text="When voting should automatically end")
    
    # Manual timing records
    manual_start_time = models.DateTimeField(null=True, blank=True,
                                            help_text="When election was manually started")
    manual_end_time = models.DateTimeField(null=True, blank=True,
                                          help_text="When election was manually ended")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Election Settings"
    
    def __str__(self):
        return f"{self.election_name} - {'ACTIVE' if self.is_active else 'INACTIVE'}"
    
    def get_voting_status(self):
        """Simple voting status check"""
        from django.utils import timezone
        
        now = timezone.now()
        
        # Manual override
        if self.is_manual_override:
            return self.is_active
        
        # Scheduled mode
        if self.scheduled_start and self.scheduled_end:
            # Simple comparison - let Django handle timezones
            return self.scheduled_start <= now <= self.scheduled_end
        
        return False
    
    def get_remaining_time(self):
        """Get remaining time - returns timedelta or None"""
        from django.utils import timezone
        
        if not self.get_voting_status():
            return None
        
        now = timezone.now()
        
        if self.scheduled_end:
            remaining = self.scheduled_end - now
            # Ensure positive time
            if remaining.total_seconds() > 0:
                return remaining
        
        return None
    
    def start_manually(self):
        """Start election manually"""
        self.is_manual_override = True
        self.is_active = True
        self.manual_start_time = timezone.now()
        self.manual_end_time = None  # Clear any previous end time
        self.save()
    
    def stop_manually(self):
        """Stop election manually"""
        self.is_manual_override = True
        self.is_active = False
        self.manual_end_time = timezone.now()
        self.save()

# Signal to create default ElectionSettings when server starts
@receiver(post_save, sender=User)
def create_default_election_settings(sender, instance, created, **kwargs):
    """Create default election settings if none exist"""
    if created and not ElectionSettings.objects.exists():
        ElectionSettings.objects.create(election_name="General Election")