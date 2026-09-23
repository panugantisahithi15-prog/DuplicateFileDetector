/**
 * scan.js – client-side helpers for the Service page.
 *
 * 1. Shows a spinner on the Scan button while the form is submitting.
 * 2. Scrolls the results section into view after the page loads
 *    (when results are present).
 * 3. Handles inline rename form toggle.
 */

(function () {
    'use strict';

    // ── Scan form spinner ──────────────────────────────────────────────────
    const scanForm = document.getElementById('scan-form');
    const scanBtn  = document.getElementById('scan-btn');

    if (scanForm && scanBtn) {
        scanForm.addEventListener('submit', function () {
            scanBtn.classList.add('loading');
            scanBtn.disabled = true;
        });
    }

    // ── Auto-scroll to results ─────────────────────────────────────────────
    const resultsSection = document.getElementById('results-section');
    if (resultsSection) {
        // Small delay so the page fully renders first
        setTimeout(function () {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 150);
    }

    // ── Rename form toggle ─────────────────────────────────────────────────
    document.querySelectorAll('.rename-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const form = document.getElementById(btn.dataset.target);
            if (form) {
                const hidden = form.style.display === 'none' || !form.style.display;
                form.style.display = hidden ? 'flex' : 'none';
                if (hidden) {
                    const input = form.querySelector('input[name="new_name"]');
                    if (input) input.focus();
                }
            }
        });
    });
}());
