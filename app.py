from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import json
import fitz  # PyMuPDF
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import mimetypes

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
# Enable CORS for frontend integration
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")

SYSTEM_PROMPT = """
You are an expert HR screening specialist with 10+ years of experience.
Evaluate the resume strictly against the job description.
Base every assessment ONLY on evidence explicitly present in the resume.
Never assume or infer skills not clearly stated.
Respond with ONLY valid JSON. No explanation, no markdown, no text outside the JSON.
Return exactly this structure:
{
  "candidate_id": "<as provided>",
  "candidate_name": "<Candidate's full name extracted from the resume (e.g. 'John Doe'). If not found, use a clean placeholder like 'Candidate'>",
  "candidate_email": "<Candidate's email address extracted from their resume (e.g. 'john.doe@gmail.com'). If not found, use a blank string ''>",
  "job_role": "<The job title or role extracted from the job description (e.g. 'AI Implementation Associate')>",
  "company_name": "<The company name extracted from the job description (e.g. 'Royal Brothers'). If not found, use 'Royal Brothers'>",
  "match_score": <integer 0-100>,
  "recommendation": "Shortlist" | "Maybe" | "Reject",
  "must_haves_met": ["<JD requirement present in resume>"],
  "must_haves_missing": ["<JD requirement absent from resume>"],
  "strengths": ["<strength with resume evidence>", "...", "..."],
  "gaps": ["<gap with evidence>", "...", "..."],
  "suggested_interview_questions": ["<question 1>", "<question 2>"],
  "reasoning": "<2-3 sentence summary explaining recommendation>"
}

SCORING GUIDE:
80-100 = Strong fit. Meets almost all must-haves. -> Shortlist
60-79  = Good fit. Minor trainable gaps. -> Likely Shortlist
40-59  = Partial fit. Missing important requirements. -> Maybe
0-39   = Poor fit. Missing critical requirements. -> Reject
"""

EMAIL_AGENT_PROMPT = """
You are an expert HR Communications Specialist.
Draft a personalized, professional email response to the candidate based on the screening evaluation.

Respond with ONLY valid JSON. No explanation, no markdown, no text outside the JSON.
Return exactly this structure:
{
  "subject": "<Compelling email subject line, customized with the company name and the job title/role>",
  "body": "<Personalized, professional email body, addressing the candidate by their extracted candidate_name (NOT by filename or extension) and referring to the specific job title and company name>"
}

TONE GUIDELINES:
- Shortlist / Likely Shortlist: Enthusiastic and welcoming. Invite them to schedule an interview at the company and specify next steps.
- Maybe: Polite and curious. Express interest in their application but ask them to clarify or provide more details on one of the key gaps identified in the screening.
- Reject: Extremely polite, encouraging, and constructive. Mention at least one specific strength from their resume so it feels personalized and human, not like an automated template.

Input evaluation details will be provided. Address the candidate using their candidate_name.
"""

def clean_json_response(raw_text):
    """
    Cleans the raw response text from the LLM, removing markdown code blocks if present,
    and parses it into a Python dictionary.
    """
    cleaned = raw_text.strip()
    # Remove markdown code blocks if the model wrapped the JSON in them
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    return json.loads(cleaned)

def generate_mock_evaluation(candidate_id, jd, error_context=None):
    """
    Generates a realistic mock candidate evaluation for offline/demo testing
    or when AIMLAPI credits are exhausted.
    """
    jd_lower = jd.lower()
    
    # Clean the candidate ID to get a clean name
    name_part = candidate_id.split('.')[0] if '.' in candidate_id else candidate_id
    if name_part.lower() in ("resume", "cv", "unknown", "candidate_1", "candidate_2", "candidate_3"):
        candidate_name = random.choice(["Aditya Sharma", "Priya Patel", "Rohan Das", "Sneha Rao", "Vikram Singh"])
    else:
        candidate_name = name_part.replace("-", " ").replace("_", " ").title()
        
    candidate_email = candidate_name.lower().replace(" ", ".") + "@example.com"
        
    # Extract job role from JD
    job_role = "AI Implementation Associate"
    if "python" in jd_lower and "react" in jd_lower:
        job_role = "Full Stack Python/React Developer"
    elif "python" in jd_lower:
        job_role = "Python Developer"
    elif "react" in jd_lower:
        job_role = "React Developer"
    elif "associate" in jd_lower or "ai" in jd_lower:
        job_role = "AI Implementation Associate"
        
    # Extract company name from JD
    company_name = "Royal Brothers"
    if "royal brothers" in jd_lower:
        company_name = "Royal Brothers"

    # Simple keyword spotter from job description
    skills = []
    if "python" in jd_lower: skills.append("Python Development")
    if "react" in jd_lower: skills.append("React Frontend Framework")
    if "javascript" in jd_lower or "js " in jd_lower: skills.append("JavaScript (ES6+)")
    if "flask" in jd_lower: skills.append("Flask RESTful APIs")
    if "django" in jd_lower: skills.append("Django Backend Framework")
    if "sql" in jd_lower or "database" in jd_lower: skills.append("Database Management & SQL")
    if "docker" in jd_lower: skills.append("Docker Containerization")
    if "kubernetes" in jd_lower: skills.append("Kubernetes Orchestration")
    if "aws" in jd_lower or "cloud" in jd_lower: skills.append("Amazon Web Services (AWS)")
    if "git" in jd_lower: skills.append("Git Version Control")
    if "machine learning" in jd_lower or "ml" in jd_lower: skills.append("Machine Learning (scikit-learn)")
    if "typescript" in jd_lower or "ts" in jd_lower: skills.append("TypeScript")
    if "html" in jd_lower or "css" in jd_lower: skills.append("HTML5 & Responsive CSS")
    
    if not skills:
        skills = ["Software Engineering Principles", "Functional & Object Oriented Programming", "Team Collaboration"]
        
    random.shuffle(skills)
    split_point = max(1, len(skills) * 2 // 3)
    met = skills[:split_point]
    missing = skills[split_point:]
    if not missing:
        missing = ["System Architecture Design"]
        
    score = random.randint(55, 95)
    
    if score >= 80:
        rec = "Shortlist"
    elif score >= 60:
        rec = "Likely Shortlist"
    elif score >= 40:
        rec = "Maybe"
    else:
        rec = "Reject"
        
    strengths = [
        f"Demonstrated competence in {met[0]} in former positions.",
        "Solid track record of project delivery highlighted in history.",
        "Clear organization and documentation of technical accomplishments."
    ]
    if len(met) > 1:
        strengths.insert(1, f"Practical application of {met[1]} in project work.")
        
    gaps = [
        f"Lacks explicit certification or deeper enterprise experience in {missing[0]}.",
        "Could benefit from more direct leadership or architectural design exposure."
    ]
    
    questions = [
        f"Can you tell us about a complex project where you leveraged {met[0]}?",
        f"How would you approach a scenario where {missing[0]} is the primary constraint?",
        "Walk us through your typical process for debugging a production latency issue."
    ]
    
    reasoning = f"The candidate has a solid resume profile matching {score}% of the target requirements. "
    if error_context:
        reasoning += f"[{error_context}]"
    else:
        reasoning += "Meets key qualifications listed in the Job Description. Recommend advancing to initial screen."
        
    # Generate mock email draft
    if rec in ("Shortlist", "Likely Shortlist"):
        email_subj = f"Next Steps: {job_role} Application at {company_name} - {candidate_name}"
        email_body = f"Dear {candidate_name},\n\nThank you for applying for the {job_role} role at {company_name}.\n\nOur team has reviewed your application and we are very impressed with your background, especially your hands-on experience in {met[0] if met else 'AI solutions'}.\n\nWe would love to invite you for a 30-minute technical discussion to learn more about the projects you have shipped. Please let us know your availability over the next few days.\n\nBest regards,\nHR Team\n{company_name}"
    elif rec == "Maybe":
        email_subj = f"Follow-up: {job_role} Application at {company_name} - {candidate_name}"
        email_body = f"Dear {candidate_name},\n\nThank you for your application for the {job_role} role at {company_name}.\n\nWe are currently reviewing your profile. To help us make an informed decision, could you provide some additional context regarding your experience with {missing[0] if missing else 'agent platforms'}?\n\nIf you have a quick description or a repository link of a project where you solved a similar issue, please share it with us. We look forward to hearing from you.\n\nBest regards,\nHR Team\n{company_name}"
    else:
        email_subj = f"Update on your application: {job_role} at {company_name} - {candidate_name}"
        email_body = f"Dear {candidate_name},\n\nThank you for taking the time to apply and share your experience with us.\n\nWhile we were impressed by your background in {met[0] if met else 'software engineering'}, we are currently looking for candidates who have more deep, hands-on experience in {missing[0] if missing else 'agent tools'}.\n\nWe appreciate your interest in {company_name} and wish you all the best in your job search.\n\nBest regards,\nHR Team\n{company_name}"

    return {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "job_role": job_role,
        "company_name": company_name,
        "match_score": score,
        "recommendation": rec,
        "must_haves_met": met,
        "must_haves_missing": missing,
        "strengths": strengths,
        "gaps": gaps,
        "suggested_interview_questions": questions,
        "reasoning": reasoning,
        "email_draft": {
            "subject": email_subj,
            "body": email_body
        }
    }

def screen_with_candidates(jd, candidates):
    """
    Shared screening logic. Iterates through candidates, sends JD + Resume content
    to Gemini API, parses responses, and returns sorted candidate analysis list.
    """
    # Force reload of environment variables on request to dynamically capture any new key in .env
    load_dotenv(override=True)
    global GEMINI_API_KEY, DEMO_MODE
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")

    # Server side input validation
    if not jd or not jd.strip():
        return jsonify({"error": "Job Description (JD) is required"}), 400
    if not candidates:
        return jsonify({"error": "At least one candidate resume is required"}), 400

    # Determine if we should run in demo/mock mode
    has_gemini = GEMINI_API_KEY and GEMINI_API_KEY.strip() != "" and GEMINI_API_KEY != "your_gemini_key_here"
    is_demo = DEMO_MODE or not has_gemini
    demo_reason = ""
    if is_demo:
        if DEMO_MODE:
            demo_reason = "DEMO MODE active via server configuration."
        else:
            demo_reason = "DEMO MODE active: GEMINI_API_KEY is not configured in .env."

    results = []
    for candidate in candidates:
        cand_id = candidate.get("id", "Unknown")
        cand_text = candidate.get("text", "")
        
        # Basic candidate data validation
        if not cand_text or not cand_text.strip():
            results.append({
                "candidate_id": cand_id,
                "error": "Resume content is empty.",
                "match_score": 0,
                "recommendation": "Error",
                "must_haves_met": [],
                "must_haves_missing": [],
                "strengths": [],
                "gaps": [],
                "suggested_interview_questions": [],
                "reasoning": "Could not screen this candidate because the resume text was empty."
            })
            continue

        if is_demo:
            # Generate mock evaluation directly
            parsed = generate_mock_evaluation(cand_id, jd, demo_reason)
            results.append(parsed)
            continue

        try:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

            # Post request to native Gemini API generateContent endpoint
            response = requests.post(
                api_url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "role": "user",
                        "parts": [{"text": f"Candidate ID: {cand_id}\n\nJOB DESCRIPTION:\n{jd}\n\nRESUME:\n{cand_text}"}]
                    }],
                    "systemInstruction": {
                        "parts": [{"text": SYSTEM_PROMPT}]
                    },
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1
                    }
                },
                timeout=30
            )

            # Check for non-200 responses and parse their error body
            if response.status_code != 200:
                err_msg = ""
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", {}).get("message") or err_json.get("message")
                except:
                    pass
                if not err_msg:
                    err_msg = response.text or f"HTTP {response.status_code}"
                
                # Check specifically for out of funds/quota
                if any(x in err_msg.lower() or x in response.text.lower() for x in ["run out of funds", "credits", "quota", "billing"]):
                    err_msg = "Your Gemini account has run out of funds or exceeded quota."
                    
                raise Exception(f"Gemini API Error ({response.status_code}): {err_msg}")
            
            response_json = response.json()
            raw_content = response_json["candidates"][0]["content"]["parts"][0]["text"]
            
            # Parse & clean the structured JSON
            parsed = clean_json_response(raw_content)
            
            # Match API spec fields
            parsed["candidate_id"] = cand_id  # ensure ID matches
            
            # Call the second agent (Email Drafter)
            try:
                email_payload = {
                    "candidate_name": parsed.get("candidate_name", cand_id),
                    "job_role": parsed.get("job_role", "AI Implementation Associate"),
                    "company_name": parsed.get("company_name", "Royal Brothers"),
                    "recommendation": parsed.get("recommendation", "Reject"),
                    "strengths": parsed.get("strengths", []),
                    "gaps": parsed.get("gaps", [])
                }
                email_response = requests.post(
                    api_url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{
                            "role": "user",
                            "parts": [{"text": f"Evaluation details:\n{json.dumps(email_payload, indent=2)}"}]
                        }],
                        "systemInstruction": {
                            "parts": [{"text": EMAIL_AGENT_PROMPT}]
                        },
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.2
                        }
                    },
                    timeout=30
                )
                if email_response.status_code == 200:
                    email_json = email_response.json()
                    raw_email_text = email_json["candidates"][0]["content"]["parts"][0]["text"]
                    parsed["email_draft"] = clean_json_response(raw_email_text)
                else:
                    raise Exception(f"Email agent HTTP {email_response.status_code}")
            except Exception as email_err:
                print(f"Warning: Email drafting agent failed for {cand_id}: {email_err}")
                # Fallback draft based on recommendation
                rec = parsed.get("recommendation", "Reject")
                cand_name = parsed.get("candidate_name", cand_id)
                job = parsed.get("job_role", "AI Implementation Associate")
                company = parsed.get("company_name", "Royal Brothers")
                if rec in ("Shortlist", "Likely Shortlist"):
                    email_subj = f"Next Steps: {job} Application at {company} - {cand_name}"
                    email_body = f"Dear {cand_name},\n\nThank you for applying for the {job} role at {company}. We've reviewed your application and would like to schedule a call. Please let us know your availability.\n\nBest regards,\nHR Team\n{company}"
                elif rec == "Maybe":
                    email_subj = f"Follow-up: {job} Application at {company} - {cand_name}"
                    email_body = f"Dear {cand_name},\n\nThank you for applying for the {job} role at {company}. We are reviewing your application. Could you please provide more details on your experience?\n\nBest regards,\nHR Team\n{company}"
                else:
                    email_subj = f"Update on your application: {job} at {company} - {cand_name}"
                    email_body = f"Dear {cand_name},\n\nThank you for applying for the {job} role at {company}. Unfortunately, we cannot move forward at this time.\n\nBest regards,\nHR Team\n{company}"
                parsed["email_draft"] = {
                    "subject": email_subj,
                    "body": email_body
                }

            results.append(parsed)
            
        except requests.exceptions.RequestException as req_err:
            err_msg = str(req_err)
            if req_err.response is not None:
                try:
                    err_json = req_err.response.json()
                    err_msg = err_json.get("message") or err_json.get("error", {}).get("message") or err_msg
                except:
                    err_msg = req_err.response.text or err_msg
            
            if any(x in err_msg.lower() for x in ["run out of funds", "credits", "quota", "billing"]):
                err_msg = "Your Gemini account has run out of funds or exceeded quota. Please top up your balance."
                # Fallback to realistic mock evaluation so the user can still see and test the dashboard
                parsed = generate_mock_evaluation(cand_id, jd, f"DEMO FALLBACK: {err_msg}")
                results.append(parsed)
            else:
                results.append({
                    "candidate_id": cand_id,
                    "error": f"API request error: {err_msg}",
                    "match_score": 0,
                    "recommendation": "Error",
                    "must_haves_met": [],
                    "must_haves_missing": [],
                    "strengths": [],
                    "gaps": [],
                    "suggested_interview_questions": [],
                    "reasoning": f"Gemini API connection failed: {err_msg}"
                })
        except Exception as e:
            err_str = str(e)
            if any(x in err_str.lower() for x in ["run out of funds", "credits", "quota", "billing"]):
                err_msg = "Your Gemini account has run out of funds or exceeded quota."
                parsed = generate_mock_evaluation(cand_id, jd, f"DEMO FALLBACK: {err_msg}")
                results.append(parsed)
            else:
                results.append({
                    "candidate_id": cand_id,
                    "error": err_str,
                    "match_score": 0,
                    "recommendation": "Error",
                    "must_haves_met": [],
                    "must_haves_missing": [],
                    "strengths": [],
                    "gaps": [],
                    "suggested_interview_questions": [],
                    "reasoning": f"Unexpected error during screening: {err_str}"
                })

    # Sort results by match_score descending
    results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return jsonify({"results": results})

@app.route("/screen", methods=["POST"])
def screen():
    data = request.json or {}
    jd = data.get("jd", "")
    candidates = data.get("candidates", [])  # list of {id, text}
    return screen_with_candidates(jd, candidates)

@app.route("/screen-pdf", methods=["POST"])
def screen_pdf():
    # Accept PDF file upload, extract text, add to candidates list
    jd = request.form.get("jd", "")
    files = request.files.getlist("resumes")
    candidates = []
    
    for i, f in enumerate(files):
        if not f or f.filename == "":
            continue
        try:
            doc = fitz.open(stream=f.read(), filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            candidates.append({"id": f.filename, "text": text})
        except Exception as pdf_err:
            # We add a candidate entry but with an error flag so it can be handled
            candidates.append({
                "id": f.filename or f"Candidate_{i+1}", 
                "text": f"Error parsing PDF file: {str(pdf_err)}"
            })

    return screen_with_candidates(jd, candidates)

@app.route("/extract-text", methods=["POST"])
def extract_text():
    files = request.files.getlist("resumes")
    candidates = []
    
    for i, f in enumerate(files):
        if not f or f.filename == "":
            continue
        try:
            doc = fitz.open(stream=f.read(), filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            candidates.append({"id": f.filename, "text": text})
        except Exception as pdf_err:
            candidates.append({
                "id": f.filename or f"Candidate_{i+1}", 
                "error": f"Error parsing PDF file: {str(pdf_err)}"
            })
            
    return jsonify({"candidates": candidates})

@app.route("/send-email", methods=["POST"])
def send_email():
    # Read fields
    to_email = request.form.get("to_email", "").strip()
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()
    
    smtp_server = request.form.get("smtp_server", "").strip()
    smtp_port = request.form.get("smtp_port", "").strip()
    smtp_user = request.form.get("smtp_user", "").strip()
    smtp_password = request.form.get("smtp_password", "").strip()
    use_smtp = request.form.get("use_smtp", "false").lower() in ("true", "1", "yes")
    
    attachments = request.files.getlist("attachments")
    
    if not to_email:
        return jsonify({"success": False, "error": "Recipient email address is required."}), 400
    if not subject:
        return jsonify({"success": False, "error": "Subject line is required."}), 400
    if not body:
        return jsonify({"success": False, "error": "Email body is required."}), 400

    if not use_smtp:
        # Mock/Demo Mode - Log email to terminal and local workspace file
        try:
            log_entry = (
                f"==================================================\n"
                f"=== DEMO EMAIL DISPATCH (NO SMTP CREDENTIALS) ===\n"
                f"Date: {request.headers.get('Host', 'localhost')}\n"
                f"To: {to_email}\n"
                f"Subject: {subject}\n"
                f"Attachments Count: {len([f for f in attachments if f.filename])}\n"
                f"Attachments List: {', '.join(f.filename for f in attachments if f.filename) or 'None'}\n"
                f"--------------------------------------------------\n"
                f"Body:\n{body}\n"
                f"==================================================\n\n"
            )
            print(log_entry)
            os.makedirs(".logs", exist_ok=True)
            with open(os.path.join(".logs", "sent_emails.log"), "a", encoding="utf-8") as f_log:
                f_log.write(log_entry)
            
            return jsonify({
                "success": True,
                "message": "Demo mode: Email printed to console and logged to '.logs/sent_emails.log' successfully."
            })
        except Exception as log_err:
            return jsonify({"success": False, "error": f"Failed to write mock log: {str(log_err)}"}), 500

    # Real SMTP Mode
    if not smtp_server or not smtp_user or not smtp_password:
        return jsonify({"success": False, "error": "SMTP configuration is incomplete. Fill in server, user, and password settings."}), 400

    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Process attachments
        for f in attachments:
            if not f or f.filename == "":
                continue
            
            file_content = f.read()
            # Guess mime-type
            content_type, encoding = mimetypes.guess_type(f.filename)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            main_type, sub_type = content_type.split('/', 1)
            part = MIMEBase(main_type, sub_type)
            part.set_payload(file_content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{f.filename}"'
            )
            msg.attach(part)
            
        # SMTP connection
        port = int(smtp_port) if smtp_port and smtp_port.isdigit() else 587
        
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_server, port, timeout=15)
            server.starttls()
            
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        
        # Log entry in local files for user record even if sent via SMTP
        os.makedirs(".logs", exist_ok=True)
        with open(os.path.join(".logs", "sent_emails.log"), "a", encoding="utf-8") as f_log:
            f_log.write(
                f"=== SMTP DISPATCH ===\n"
                f"To: {to_email}\n"
                f"Subject: {subject}\n"
                f"Status: Success\n"
                f"Attachments: {', '.join(f.filename for f in attachments if f.filename) or 'None'}\n"
                f"=====================\n\n"
            )
            
        return jsonify({"success": True, "message": "Email sent successfully via SMTP!"})
        
    except smtplib.SMTPAuthenticationError:
        return jsonify({"success": False, "error": "SMTP Authentication failed. Please check your username and password/app password."}), 401
    except Exception as e:
        return jsonify({"success": False, "error": f"SMTP Dispatch Error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
