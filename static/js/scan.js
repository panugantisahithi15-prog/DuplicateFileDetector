/**
 * scan.js – client-side helpers for the Service and Action pages.
 *
 * 1. Path-mode: shows a spinner on the Scan button while submitting.
 * 2. Auto-scrolls to the results section after load.
 * 3. Browse-mode: folder picker → shows selected folder name + file count
 *    → submits the hidden upload form.
 * 4. Panel toggle: "or type a path manually" / "← pick a folder instead".
 * 5. Action page: inline rename form toggle.
 */

(function () {
    'use strict';

    // ── 1. Path-mode scan form spinner ──────────────────────────────────────
    var scanForm = document.getElementById('scan-form');
    var scanBtn  = document.getElementById('scan-btn');

    if (scanForm && scanBtn) {
        scanForm.addEventListener('submit', function () {
            scanBtn.classList.add('loading');
            scanBtn.disabled = true;
        });
    }

    // ── 2. Auto-scroll to results ────────────────────────────────────────────
    var resultsSection = document.getElementById('results-section');
    if (resultsSection) {
        setTimeout(function () {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 150);
    }

    // ── 3 & 4. Browse-mode folder picker + panel toggle ─────────────────────
    var browsePanel    = document.getElementById('browse-panel');
    var pathPanel      = document.getElementById('path-panel');
    var showPathBtn    = document.getElementById('show-path-btn');
    var showBrowseBtn  = document.getElementById('show-browse-btn');
    var browseBtn      = document.getElementById('browse-btn');
    var folderInput    = document.getElementById('folder-input');
    var folderInfo     = document.getElementById('folder-info');
    var folderNameText = document.getElementById('folder-name-text');
    var fileCountBadge = document.getElementById('file-count-badge');
    var uploadScanBtn  = document.getElementById('upload-scan-btn');
    var uploadForm     = document.getElementById('upload-form');

    // Panel toggle
    if (showPathBtn && browsePanel && pathPanel) {
        showPathBtn.addEventListener('click', function () {
            browsePanel.style.display = 'none';
            pathPanel.style.display   = '';
        });
    }
    if (showBrowseBtn && browsePanel && pathPanel) {
        showBrowseBtn.addEventListener('click', function () {
            pathPanel.style.display   = 'none';
            browsePanel.style.display = '';
        });
    }

    // "Choose Folder" button triggers the hidden file input
    if (browseBtn && folderInput) {
        browseBtn.addEventListener('click', function () {
            folderInput.click();
        });
    }

    // After folder selection: show name, count, and Scan button
    if (folderInput) {
        folderInput.addEventListener('change', function () {
            var files = folderInput.files;
            if (!files || !files.length) return;

            // Root folder name is the first segment of webkitRelativePath
            var rootName = (files[0].webkitRelativePath || files[0].name).split('/')[0];

            folderNameText.textContent  = '📁 ' + rootName;
            fileCountBadge.textContent  = files.length + (files.length === 1 ? ' file' : ' files');

            folderInfo.style.display    = '';
            uploadScanBtn.style.display = '';
            uploadScanBtn.disabled      = false;
            browseBtn.style.display     = 'none';
        });
    }

    // Scan button: add loading state, then submit upload form
    if (uploadScanBtn && uploadForm) {
        uploadScanBtn.addEventListener('click', function () {
            uploadScanBtn.classList.add('loading');
            uploadScanBtn.disabled = true;
            uploadForm.submit();
        });
    }

    // ── 5. Action page: rename form toggle ───────────────────────────────────
    document.querySelectorAll('.rename-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var form = document.getElementById(btn.dataset.target);
            if (form) {
                var hidden = form.style.display === 'none' || !form.style.display;
                form.style.display = hidden ? 'flex' : 'none';
                if (hidden) {
                    var input = form.querySelector('input[name="new_name"]');
                    if (input) input.focus();
                }
            }
        });
    });

}());
