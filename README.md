# HR Resume Screening Agent

An AI-powered resume screening and candidate ranking application using Google Gemini 2.5 Flash.

This production-ready tool evaluates candidate resumes against job descriptions, parses details, computes match scores, categorizes fit (Shortlist, Maybe, Reject), lists met/missing must-haves, identifies strengths/gaps, suggests tailored interview questions, and exports rankings to CSV.

## Features
- **Multi-Agent Pipeline:**
  - **Agent 1 (Screening Specialist):** Evaluates candidate resumes against the job description to compute match scores, assess requirements met/missing, identify strengths/gaps, and formulate targeted interview questions.
  - **Agent 2 (HR Communications Specialist):** Uses Agent 1's findings to draft candidate-specific emails, dynamically pulling the candidate's actual name, job role, and company name with tone styles aligned to the recommendation (enthusiastic for shortlists, constructive for rejects, curious/engaging for maybes).
- **Interactive Email Drafting:** Recruiter-editable email recipient address, subject line, and body input boxes embedded directly within each candidate result card. Changes sync in real-time to prevent data loss.
- **Dynamic File Attachments:** Select and attach multiple files (documents, images, videos) to candidate emails. Shows visual size, type, and name badges with quick-deletion options.
- **Automated Dispatch Options:**
  - **Individual Send:** Click "Send Email" on a single candidate card to dispatch that draft via SMTP.
  - **Batch Dispatch (Send All):** Trigger a custom confirm toast to sequence email dispatches to all candidates automatically, with throttled SMTP connections and progress indicators.
- **Modern Dark UI:** Sleek glassmorphic dashboard (`#08080C`) with glowing ambient glows, SVG radial match gauges, card fade-in transitions, and interactive confirmation warning toast modals.
- **Dual Input Modes:**
  - **Text Mode:** Add, remove, and type candidate resumes dynamically.
  - **PDF Mode:** Drag and drop or browse to upload multiple PDF resumes.
- **Real-Time Progress Tracking:** Sequential batch progress bars and status banners that update candidate-by-candidate during screening.
- **SMTP Settings Modal:** Client-side SMTP configuration panel stored securely in `localStorage` for mail server integration.
- **Billing/Credit Fallbacks:** Demo mode fallback with full dummy evaluations if API credentials are not set.

---

## Setup Instructions

### 1. Get your Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com).
2. Sign in with your Google account.
3. Click **Get API key** and generate a new API key.
4. Copy the key.

### 2. Configure the Environment
- Open the `.env` file in the root directory.
- Add your key to your environment variables:
  ```env
  GEMINI_API_KEY=your_gemini_key_here
  ```
*Note: If the key is missing or left as the default placeholder, the application will run in local **Demo Mode**, displaying mock evaluations for offline testing.*

### 3. Install Dependencies
Make sure you have Python 3.8+ installed. Set up a virtual environment and install the required packages:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 4. Run the Backend Server
Start the Flask application:
```bash
python app.py
```
The server will boot up and start listening at `http://localhost:5000`.

### 5. Launch the Frontend
You can open `index.html` directly in any web browser by double-clicking the file, or you can serve it using a lightweight HTTP server:
```bash
# Run a Python-based server in another terminal window
python -m http.server 3000
```
Then visit `http://localhost:3000` in your web browser.

---

## File Structure
- `index.html`: Modern, responsive single-file user interface.
- `app.py`: Flask backend, handles PDF text extraction (`fitz`) and secure Gemini completions.
- `.env`: Environment variables (holds your secret Gemini API key).
- `requirements.txt`: Python package dependencies.
- `README.md`: Setup instructions and documentation.
