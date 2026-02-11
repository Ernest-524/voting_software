from django.contrib import admin
from . import models
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
# Register your models here.
admin.site.register(models.Position)
admin.site.register(models.Candidate)
admin.site.register(models.Vote)

admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'is_staff')
    list_filter = ('first_name',)
    search_fields = ('first_name',)