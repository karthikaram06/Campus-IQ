#!/usr/bin/env bash

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput

python manage.py migrate

python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get("DJANGO_ADMIN_USERNAME")
email = os.environ.get("DJANGO_ADMIN_EMAIL", "")
password = os.environ.get("DJANGO_ADMIN_PASSWORD")

if username and password:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )

    if created:
        user.set_password(password)
        user.save()
        print("Render admin user created.")
    else:
        print("Render admin user already exists.")
PY