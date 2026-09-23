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
from detector.service import find_duplicates

# ── App setup ──────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["WTF_CSRF_ENABLED"] = True

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

    if form.validate_on_submit():
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


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Bind to localhost only – never 0.0.0.0
    app.run(host="127.0.0.1", port=5000, debug=False)
