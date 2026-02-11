from django import forms
from .models import Position, Candidate, Vote, ElectionSettings

class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['position_name', 'description']

class CandidateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['candidate_name', 'photo', 'candidate_position']
        widgets = {
            'candidate_name': forms.Select(attrs={'id': 'id_candidate_name'}),
        }

class VotingForm(forms.Form):
    def __init__(self, *args, **kwargs):
        positions = kwargs.pop('positions', Position.objects.all())
        super().__init__(*args, **kwargs)
        
        for position in positions:
            candidates = position.candidate_position.all()
            
            if candidates.count() > 1:
                # Multiple candidates - show radio buttons to select one
                self.fields[f'position_{position.id}'] = forms.ChoiceField(
                    choices=[(candidate.id, f"{candidate.candidate_name.first_name} {candidate.candidate_name.last_name}") 
                            for candidate in candidates],
                    widget=forms.RadioSelect(attrs={'class': 'candidate-radio'}),
                    label=f"Select candidate for {position.position_name}:",
                    required=True
                )
            else:
                # Single candidate - show yes/no for each candidate
                for candidate in candidates:
                    self.fields[f'candidate_{candidate.id}'] = forms.ChoiceField(
                        choices=[('yes', 'Yes'), ('no', 'No')],
                        widget=forms.RadioSelect(attrs={'class': 'yes-no-radio'}),
                        label=f"{candidate.candidate_name.first_name} {candidate.candidate_name.last_name}",
                        required=True
                    )

class CustomLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class ElectionSettingsForm(forms.ModelForm):
    class Meta:
        model = ElectionSettings
        fields = [
            'election_name', 
            'scheduled_start', 
            'scheduled_end',
            'is_manual_override',
            'is_active',
            'manual_start_time',
            'manual_end_time'
        ]
        widgets = {
            'scheduled_start': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'scheduled_end': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'manual_start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'manual_end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'election_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make checkboxes look nicer
        self.fields['is_manual_override'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_active'].widget.attrs.update({'class': 'form-check-input'})
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_start = cleaned_data.get('scheduled_start')
        scheduled_end = cleaned_data.get('scheduled_end')
        is_manual_override = cleaned_data.get('is_manual_override')
        
        # Only validate schedule if NOT using manual override
        if not is_manual_override:
            if scheduled_start and scheduled_end:
                if scheduled_end <= scheduled_start:
                    raise forms.ValidationError("End time must be after start time.")
        
        return cleaned_data