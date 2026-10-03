"""
Application configuration.
All tuneable constants live here so they're easy to find.
"""

import os
import secrets

# ── Flask ──────────────────────────────────────────────────────────────────
# Set this to a stable value in production (env var recommended).
SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))

# ── Scanner ────────────────────────────────────────────────────────────────
# Minimum file size to consider (bytes).  1 = skip zero-byte files only.
MIN_FILE_SIZE = 1

# ── File upload ───────────────────────────────────────────────────────────
# Maximum total upload size for the folder-upload feature.
# Raise this if you regularly scan large folders via the browser picker.
MAX_UPLOAD_SIZE = 200 * 1024 * 1024   # 200 MB

# ── In-memory scan store ───────────────────────────────────────────────────
# Max number of scan results to keep in memory at once.
MAX_STORED_SCANS = 20
