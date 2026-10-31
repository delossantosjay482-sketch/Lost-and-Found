"""STEP 4 - Input validation. Every function raises ValueError with a friendly message."""
import os
import re
from datetime import date, datetime

CATEGORIES = ("Bags", "Electronics", "Clothing", "Documents / IDs", "Accessories", "Books", "Keys", "Bottles", "Others")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
PHONE_RE = re.compile(r"^\+?[\d\-\s]{10,16}$")


def validate_login(username, password):
    username = username.strip()
    if not username or not password:
        raise ValueError("Please enter your username and password.")
    return username, password


def validate_registration(full_name, student_id, username, password, confirm):
    full_name, student_id, username = " ".join(full_name.split()), student_id.strip().upper(), username.strip()
    if len(full_name) < 3 or not re.fullmatch(r"[A-Za-z.\-' ]+", full_name):
        raise ValueError("Enter your full name (letters only, at least 3 characters).")
    if not re.fullmatch(r"[A-Z0-9-]{4,20}", student_id):
        raise ValueError("Student ID must be 4-20 letters/numbers (e.g. CA202409529).")
    if not re.fullmatch(r"[A-Za-z0-9_.]{4,20}", username):
        raise ValueError("Username must be 4-20 characters: letters, numbers, _ or .")
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Password must be 8+ characters with letters and numbers.")
    if password != confirm:
        raise ValueError("Passwords do not match.")
    return full_name, student_id, username, password


def validate_image(path):
    if not path or not os.path.isfile(path):
        raise ValueError("The selected file could not be found.")
    if not path.lower().endswith(IMAGE_EXT):
        raise ValueError("Please choose an image file (png, jpg, jpeg, gif, bmp, webp).")
    if os.path.getsize(path) > 10 * 1024 * 1024:
        raise ValueError("Image must be smaller than 10 MB.")


def validate_report(kind, name, category, description, date_iso, location, contact, photo):
    name, description, location, contact = name.strip(), description.strip(), location.strip(), contact.strip()
    if len(name) < 2:
        raise ValueError("Item name is required.")
    if category not in CATEGORIES:
        raise ValueError("Please select a category.")
    if len(description) < 3:
        raise ValueError("Please describe the item (color, brand, marks).")
    if len(location) < 2:
        raise ValueError("Location is required.")
    try:
        if datetime.strptime(date_iso, "%Y-%m-%d").date() > date.today():
            raise ValueError("The date cannot be in the future.")
    except ValueError as e:
        if "future" in str(e):
            raise
        raise ValueError("Please select a valid date.")
    if not (EMAIL_RE.match(contact) or PHONE_RE.match(contact)):
        raise ValueError("Contact info must be a valid email or phone number.")
    if photo:
        validate_image(photo)
    return {"kind": kind, "name": name, "category": category, "description": description,
            "date": date_iso, "location": location, "contact": contact, "photo": photo}