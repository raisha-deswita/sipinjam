# Sistem Peminjaman Alat
Internal system for managing equipment loans with role-based access.

## Features
- Custom user roles (admin, petugas, user)
- Role-based dashboards
- Inventory management (Kategori Alat, Alat)
- Activity logging
- Django authentication

## Tech Stack
- Django
- MySQL (dev)
- Python 3

## Setup
```bash
python -m venv venv
source .venv/Scripts/Activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
