from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import resolve, reverse
from test_plus import TestCase

from .forms import CustomUserCreationForm
from .models import *
from .views import *
