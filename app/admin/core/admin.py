import json

from django.urls import path
from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from django.contrib.auth.models import Group, User as AuthUser


admin.site.unregister(Group)
admin.site.unregister(AuthUser)
