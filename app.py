import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect
import mysql.connector

from gemini import analyze_email, parse_analysis
from zoho import get_access_token, get_emails, get_email_content, clean_email_content

# Load environment variables from .env file
load_dotenv()

def create_connection():
    """Establishes a connection to the MySQL database using environment variables."""
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "root")
    db_password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "smartmail")
    db_ssl_ca = os.getenv("DB_SSL_CA")

    connect_args = {
        "host": db_host,
        "port": db_port,
        "user": db_user,
        "password": db_password,
        "database": db_name
    }

    # If an SSL CA file is specified, configure it
    if db_ssl_ca:
        # Resolve path relative to this script's directory if it is a relative path
        if not os.path.isabs(db_ssl_ca):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            connect_args["ssl_ca"] = os.path.join(base_dir, db_ssl_ca)
        else:
            connect_args["ssl_ca"] = db_ssl_ca

    return mysql.connector.connect(**connect_args)

# Establish the initial database connection
conn = None
cursor = None

try:
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)
except Exception as e:
    print(f"Initial database connection failed: {e}")

app = Flask(__name__)


@app.before_request
def check_db_connection():
    global conn, cursor
    try:
        # If connection doesn't exist or is not connected, establish a new one
        if conn is None or not conn.is_connected():
            conn = create_connection()
            cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"Database reconnection failed: {e}")


@app.route("/")
def home():
    return render_template("home.html")


def load_mailbox(selected_id=None, analysis_error=None):
    cursor.execute("SELECT * FROM emails ORDER BY created_at DESC")
    emails = cursor.fetchall()

    selected = None
    if selected_id is not None:
        cursor.execute("SELECT * FROM emails WHERE id=%s", (selected_id,))
        selected = cursor.fetchone()

    return render_template(
        "mailbox.html",
        emails=emails,
        selected=selected,
        analysis_error=analysis_error
    )


def analyze_and_store_email(email_id, email):
    try:
        result = analyze_email(email["subject"], email["body"])
    except Exception:
        return "AI analysis is busy right now. Please try again after a few minutes."

    tone, summary, reply = parse_analysis(result)
    if not tone or not summary or not reply:
        return "AI analysis returned an incomplete response. Please try again after a few minutes."

    cursor.execute(
        """
        UPDATE emails
        SET tone=%s, summary=%s, reply=%s
        WHERE id=%s
        """,
        (tone, summary, reply, email_id)
    )
    conn.commit()
    return None


@app.route("/mailbox")
def mailbox():
    return load_mailbox()


@app.route("/mail/<int:id>")
def mail(id):
    cursor.execute("SELECT * FROM emails WHERE id=%s", (id,))
    email = cursor.fetchone()

    if not email["tone"] or not email["summary"] or not email["reply"]:
        analysis_error = analyze_and_store_email(id, email)
        if analysis_error is not None:
            return load_mailbox(id, analysis_error)

        cursor.execute("SELECT * FROM emails WHERE id=%s", (id,))
        email = cursor.fetchone()

    return load_mailbox(id)


@app.route("/reanalyze/<int:id>")
def reanalyze(id):
    cursor.execute("SELECT * FROM emails WHERE id=%s", (id,))
    email = cursor.fetchone()

    analysis_error = analyze_and_store_email(id, email)
    if analysis_error is not None:
        return load_mailbox(id, analysis_error)

    return redirect(f"/mail/{id}")


@app.route("/sync")
def sync():
    try:
        access_token = get_access_token()
        data = get_emails(access_token=access_token)
    except RuntimeError as error:
        return f"Sync failed: {error}. Try again after a few minutes."

    for mail in data["data"]:
        content = get_email_content(mail["folderId"], mail["messageId"], access_token=access_token)
        body = clean_email_content(content)

        if not body:
            body = mail.get("summary") or ""

        cursor.execute(
            """
            INSERT IGNORE INTO emails (zoho_message_id, sender_email, subject, body)
            VALUES (%s, %s, %s, %s)
            """,
            (mail["messageId"], mail["fromAddress"], mail["subject"], body)
        )

        cursor.execute(
            """
            UPDATE emails
            SET sender_email=%s, subject=%s, body=%s
            WHERE zoho_message_id=%s
            """,
            (mail["fromAddress"], mail["subject"], body, mail["messageId"])
        )

    conn.commit()
    return "Sync Complete!"


if __name__ == "__main__":
    app.run(debug=True)