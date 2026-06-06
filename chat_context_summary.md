# Antigravity Session Context & Handover Summary

This document captures the complete design state, architectural decisions, and all issues resolved for the **HR Resume Screening Agent** project. Use this file as a context prompt when starting a new pair-programming session in Antigravity to continue work without losing progress.

---

## 1. Project Overview & Architecture
* **Goal:** A premium, web-based HR screening utility that ranks candidates by evaluating resumes against a Job Description, drafts personalized responder emails, and sends them via SMTP.
* **Backend (`app.py`):** Flask server containing:
  * Native Google Gemini REST integration (`gemini-3-flash-preview:generateContent` / `gemini-2.5-flash` endpoint) for streaming JSON responses.
  * PDF text extraction route (`/extract-text`) using `PyMuPDF`.
  * Secure SMTP mail dispatch route (`/send-email`) that handles raw text body inputs and binary file attachments.
  * Environmental hot-reloading for API credentials and log writing to hidden `.logs/` folder.
* **Frontend (`index.html`):** Dark-themed dashboard with glassmorphic visuals (`#08080C`), glowing violet/orange highlights, and dynamic transition animations.

---

## 2. Multi-Agent System Design
* **Agent 1 (Screening Specialist):** Compares candidate resumes with the Job Description. Extracts candidate name, email, match score, recommendation category, must-haves met/missing, strengths, gaps, and suggested interview questions.
* **Agent 2 (Communications Specialist):** Takes Agent 1's analysis and drafts a personalized email response (subject and body), addressing the candidate by name (avoiding filenames) and reflecting candidate-specific feedback (enthusiastic for Shortlists, constructive for Rejects, curious/engaging for Maybes).

---

## 3. Premium UI/UX Design System
* **Theme:** Glassmorphism, deep dark background with glowing highlights.
* **Match Score Gauges:** Circular radial SVG charts illustrating match percentage (`green` for >= 70%, `yellow` for >= 40%, `red` otherwise).
* **Tabbed Setup Interface:** Easily switch between direct text-copying and PDF drag-and-drop resume uploading.
* **Stateful Accordions:** Split candidate report metrics (Must-haves met, Must-haves missing, Strengths, Gaps, Questions, Drafted Emails) into structured expandable slots.
* **Modern Toast System:** Real-time feedback alerts (Success, Warning, Error) stacked cleanly at the top-right.

---

## 4. Issues Resolved & Code Fixes (June 2026)

### Issue A: Page Refreshes and State Loss during Email Send
* **Symptoms:** Click actions on cards caused page refreshes, wiping out current screening scores.
* **Fixes:**
  1. Standardized all button elements to specify `type="button"` (stopping browsers from defaulting to `type="submit"`).
  2. Applied `event.preventDefault()` and `event.stopPropagation()` to all event listeners to isolate event propagation.
  3. Synced active user data (Job Description, screening results) into `sessionStorage` and restored them dynamically on page reload.
  4. Added `oninput` handlers on editable subject/body inputs to save customizations to `sessionStorage` in real-time.

### Issue B: Live-Reload Loop during Logging
* **Symptoms:** Writing SMTP mock logs to the root workspace triggered folder-watcher refreshes in dev-servers, resetting the web page.
* **Fixes:** Redirected Flask backend logging to a hidden directory (`.logs/sent_emails.log`). Standard directory watch-filters ignore dotfiles, halting automated reloads.

### Issue C: Attach Files Button was Unresponsive / Hover Blocked
* **Symptoms:** Recruiter couldn't hover over or click the "Attach Files" button inside the email drafting accordion.
* **Fixes:** Discovered a mismatched, duplicate closing `</div>` tag directly following the body editor wrapper (around line 2271). This closed the parent `.accordion-body` early, causing the DOM parser to misalign layouts and overlay invisible container boxes from sibling elements on top of the button. Removed the stray tag to re-align the DOM tree.

### Issue D: File Input Dialog Suppressed on Re-Selection
* **Symptoms:** Clicking "Attach Files" (or uploading resumes) worked once, but stopped working if the user removed a file and tried to attach/upload it again.
* **Fixes:** Web browsers suppress the file input's `onchange` handler if the user picks the same file name, as the input value hasn't "changed". Added a reset line (`input.value = "";` and `e.target.value = "";`) at the end of the file processing callbacks.

### Issue E: Standard Browser Confirmation Dialog
* **Symptoms:** The "Send All Emails" button popped up the native, unstyled browser `confirm()` modal, looking disjointed from the premium design.
* **Fixes:** Replaced `confirm()` with a custom asynchronous `Promise`-based **Warning Toast Confirmation** containing styled actions ("Cancel" and "Confirm") styled with the page's color schemes.

### Issue F: Layout Clipping on Growing Accordion Content
* **Symptoms:** Long email bodies combined with multiple attachments overflowed and clipped out of the accordion container.
* **Fixes:** Increased the max-height styling limit of active accordions (`.accordion-item.active .accordion-content`) from `1000px` to `2500px` in the stylesheet.

---

## 5. Planned Future Upgrades
* **Backend Migration to Django:** Transition the backend service from Flask to Django to support robust, production-grade features, database migrations, and built-in administrative tools.
* **Authentication System:** Add a complete candidate/recruiter registration and login page with session security, SMTP-based account validation, and role-based permissions (admin vs recruiter).
* **Animated Landing Page:** Design and build a fantastic, highly animated, premium landing page introducing the screening suite, featuring interactive graphics and scrolling visual indicators.

---

## 6. Current File Locations
* **Frontend:** [index.html](file:///d:/PySpiders/HR%20-%20Screening%20tool/index.html)
* **Backend:** [app.py](file:///d:/PySpiders/HR%20-%20Screening%20tool/app.py)
* **API Configuration:** [.env](file:///d:/PySpiders/HR%20-%20Screening%20tool/.env)

