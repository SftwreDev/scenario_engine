"""
Local (development) settings.
Loads all defaults from base.py and applies development-friendly overrides.
"""

import dj_database_url

# Import all base settings
from .base import *

# Development overrides
DEBUG = True
ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}
