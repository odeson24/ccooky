"""
Simple test to verify the Flask app structure
"""
import sys
import os

# Test imports
try:
    from flask import Flask
    print("✓ Flask imported successfully")
except ImportError as e:
    print(f"✗ Failed to import Flask: {e}")
    sys.exit(1)

try:
    import requests
    print("✓ requests imported successfully")
except ImportError as e:
    print(f"✗ Failed to import requests: {e}")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    print("✓ python-dotenv imported successfully")
except ImportError as e:
    print(f"✗ Failed to import python-dotenv: {e}")
    sys.exit(1)

# Test app import
try:
    import app as flask_app
    print("✓ app.py imported successfully")
except Exception as e:
    print(f"✗ Failed to import app.py: {e}")
    sys.exit(1)

# Verify routes
try:
    app = flask_app.app
    routes = [str(rule) for rule in app.url_map.iter_rules()]
    print(f"\n✓ Found {len(routes)} routes:")
    for route in routes:
        print(f"  - {route}")
except Exception as e:
    print(f"✗ Failed to get routes: {e}")
    sys.exit(1)

print("\n✓ All tests passed! The application is ready to run.")
print("\nTo start the application:")
print("1. Copy .env.example to .env")
print("2. Add your GitLab credentials to .env")
print("3. Run: python app.py")
