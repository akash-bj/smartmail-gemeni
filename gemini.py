import os
import re
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Using the fast and cost-effective free gemini-2.5-flash model
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"


def analyze_email(subject, body):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured in .env file.")

    prompt = f"""Analyze the following email and return three fields: Tone, Summary, and Suggested Reply.
You MUST output your response enclosing each section in XML-like tags, exactly like this:
<tone>Positive, Negative, or Neutral (choose EXACTLY one of these three values, do not write a sentence)</tone>
<summary>write a brief summary of the email here</summary>
<reply>write a polite suggested reply to the email here</reply>

Here is the email to analyze:
Subject: {subject}
Body: {body}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(
            GEMINI_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=45
        )

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API returned HTTP {response.status_code}: {response.text}")

        data = response.json()
        if "candidates" not in data or not data["candidates"]:
            raise RuntimeError(f"Invalid response from Gemini API: {response.text}")

        content = data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Verify that the parsed fields are not empty
        tone, summary, reply = parse_analysis(content)
        if not (tone and summary and reply):
            missing = [f for f, val in [("tone", tone), ("summary", summary), ("reply", reply)] if not val]
            raise ValueError(f"Gemini API returned an incomplete response (missing: {', '.join(missing)})")

        return content

    except Exception as e:
        raise RuntimeError(f"Gemini API analysis failed: {e}")


def parse_analysis(text):
    tone, summary, reply = "", "", ""
    if not text:
        return tone, summary, reply

    # 1. Try XML tag parsing
    tone_match = re.search(r"<tone>(.*?)</tone>", text, re.DOTALL | re.IGNORECASE)
    summary_match = re.search(r"<summary>(.*?)</summary>", text, re.DOTALL | re.IGNORECASE)
    reply_match = re.search(r"<reply>(.*?)</reply>", text, re.DOTALL | re.IGNORECASE)

    if tone_match:
        tone = tone_match.group(1).strip()
    if summary_match:
        summary = summary_match.group(1).strip()
    if reply_match:
        reply = reply_match.group(1).strip()

    # 2. Try JSON parsing
    if not (tone and summary and reply):
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                if not tone and "tone" in data:
                    tone = str(data["tone"]).strip()
                if not summary and "summary" in data:
                    summary = str(data["summary"]).strip()
                if not reply and "reply" in data:
                    reply = str(data["reply"]).strip()
                if not reply and "suggested_reply" in data:
                    reply = str(data["suggested_reply"]).strip()
            except Exception:
                pass

    # 3. Try standard colon prefix matching (case-insensitive)
    if not (tone and summary and reply):
        for line in text.split("\n"):
            clean_line = line.replace("**", "").strip()
            if not tone:
                m = re.match(r"^tone:\s*(.*)$", clean_line, re.IGNORECASE)
                if m:
                    tone = m.group(1).strip()
            if not summary:
                m = re.match(r"^summary:\s*(.*)$", clean_line, re.IGNORECASE)
                if m:
                    summary = m.group(1).strip()
            if not reply:
                m = re.match(r"^(?:reply|suggested reply):\s*(.*)$", clean_line, re.IGNORECASE)
                if m:
                    reply = m.group(1).strip()

    # 4. Fallback search (anywhere in text)
    if not tone:
        m = re.search(r"tone:\s*(.*?)(?=\n|$|summary:|reply:)", text, re.IGNORECASE | re.DOTALL)
        if m:
            tone = m.group(1).strip()
    if not summary:
        m = re.search(r"summary:\s*(.*?)(?=\n|$|tone:|reply:)", text, re.IGNORECASE | re.DOTALL)
        if m:
            summary = m.group(1).strip()
    if not reply:
        m = re.search(r"(?:reply|suggested reply):\s*(.*?)(?=\n|$|tone:|summary:)", text, re.IGNORECASE | re.DOTALL)
        if m:
            reply = m.group(1).strip()

    # Normalize tone to exactly 'Positive', 'Negative', or 'Neutral'
    if tone:
        tone_lower = tone.lower()
        if "positive" in tone_lower:
            tone = "Positive"
        elif "negative" in tone_lower:
            tone = "Negative"
        else:
            tone = "Neutral"
    else:
        tone = "Neutral"

    return tone, summary, reply
