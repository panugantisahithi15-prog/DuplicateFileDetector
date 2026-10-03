"""
Flask entry point for Duplicate File Manager.

Binds to 127.0.0.1 only – never expose this app on a public interface
without adding authentication, because it has access to the local filesystem.
"""

from __future__ import annotations

import uuid
from collections import OrderedDict

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField
from wtforms.validators import DataRequired

import config
from detector.actions import get_action_log, rename_file, trash_file
from detector.service import find_duplicates, find_duplicates_from_uploads

# ── App setup ──────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["WTF_CSRF_ENABLED"] = True
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_SIZE

csrf = CSRFProtect(app)

# ── In-memory scan store ───────────────────────────────────────────────────
# Maps scan_id (str) -> ScanResult.
# Using OrderedDict so we can evict the oldest scan when the limit is reached.
_scan_store: OrderedDict = OrderedDict()


def _store_scan(result) -> str:
    scan_id = uuid.uuid4().hex
    _scan_store[scan_id] = result
    # Evict oldest if over the limit
    while len(_scan_store) > config.MAX_STORED_SCANS:
        _scan_store.popitem(last=False)
    return scan_id


def _get_scan(scan_id: str):
    return _scan_store.get(scan_id)


# ── Forms ──────────────────────────────────────────────────────────────────

class ScanForm(FlaskForm):
    folder = StringField("Folder path", validators=[DataRequired()])


# ── Routes ────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("home.html")


@app.route("/service", methods=["GET", "POST"])
def service():
    form = ScanForm()
    result = None
    scan_id = None

    if request.method == "POST":
        if request.form.get("upload_mode") == "1":
            # ── File-upload mode ─────────────────────────────────────────────
            uploaded = request.files.getlist("folder_files")
            # Filter out the empty sentinel Werkzeug adds when no file chosen
            uploaded = [f for f in uploaded if f.filename]
            if not uploaded:
                flash("No files received. Please choose a folder and try again.", "error")
            else:
                result = find_duplicates_from_uploads(uploaded, min_size=config.MIN_FILE_SIZE)
                if result.error:
                    flash(result.error, "error")
                else:
                    scan_id = _store_scan(result)
                    if result.group_count == 0:
                        flash("No duplicate files found in the uploaded folder ✓", "info")
        elif form.validate_on_submit():
            # ── Path mode (existing) ─────────────────────────────────────────
            folder = form.folder.data.strip()
            result = find_duplicates(folder, min_size=config.MIN_FILE_SIZE)
            if result.error:
                flash(result.error, "error")
            else:
                scan_id = _store_scan(result)
                if result.group_count == 0:
                    flash("No duplicate files found. Your folder is clean ✓", "info")

    return render_template("service.html", form=form, result=result, scan_id=scan_id)


@app.route("/action")
def action():
    scan_id = request.args.get("scan_id", "")
    group_id = request.args.get("group_id", type=int, default=None)

    result = _get_scan(scan_id) if scan_id else None
    group = None

    if result and group_id is not None:
        matching = [g for g in result.groups if g.group_id == group_id]
        group = matching[0] if matching else None

    return render_template(
        "action.html",
        result=result,
        group=group,
        scan_id=scan_id,
        action_log=get_action_log(),
    )


@app.route("/action/trash", methods=["POST"])
def action_trash():
    """Trash a single file from a duplicate group."""
    scan_id = request.form.get("scan_id", "")
    group_id = request.form.get("group_id", type=int, default=None)
    file_index = request.form.get("file_index", type=int, default=None)

    result = _get_scan(scan_id)
    if not result or group_id is None or file_index is None:
        flash("Invalid request.", "error")
        return redirect(url_for("action"))

    matching = [g for g in result.groups if g.group_id == group_id]
    if not matching:
        flash("Group not found.", "error")
        return redirect(url_for("action", scan_id=scan_id))

    group = matching[0]
    success, message = trash_file(group, file_index)

    flash(message, "success" if success else "error")
    return redirect(url_for("action", scan_id=scan_id, group_id=group_id))


@app.route("/action/rename", methods=["POST"])
def action_rename():
    """Rename a single file in a duplicate group."""
    scan_id = request.form.get("scan_id", "")
    group_id = request.form.get("group_id", type=int, default=None)
    file_index = request.form.get("file_index", type=int, default=None)
    new_name = request.form.get("new_name", "").strip()

    result = _get_scan(scan_id)
    if not result or group_id is None or file_index is None or not new_name:
        flash("Invalid request.", "error")
        return redirect(url_for("action"))

    matching = [g for g in result.groups if g.group_id == group_id]
    if not matching:
        flash("Group not found.", "error")
        return redirect(url_for("action", scan_id=scan_id))

    group = matching[0]
    success, message = rename_file(group, file_index, new_name)

    flash(message, "success" if success else "error")
    return redirect(url_for("action", scan_id=scan_id, group_id=group_id))


@app.route("/about")
def about():
    return render_template("about.html")


@app.errorhandler(413)
def upload_too_large(e):
    flash(
        f"Upload too large. The folder exceeds the {config.MAX_UPLOAD_SIZE // (1024*1024)} MB limit. "
        "Use the 'Type Path' mode instead to scan large folders without uploading.",
        "error",
    )
    return redirect(url_for("service"))


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 0.0.0.0 makes Flask reachable on all network interfaces (including
    # your phone on the same Wi-Fi).  Access it at http://<laptop-IP>:5000
    # Find your IP: run  ipconfig  (Windows) or  ip a  (Linux/macOS).
    app.run(host="0.0.0.0", port=5000, debug=False)
