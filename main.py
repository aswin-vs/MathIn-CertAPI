# from dotenv import load_dotenv
# load_dotenv()

import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from certificateReady import generateCertificate
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Firebase credentials from environment variables
firebase_credentials = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
}

if not all(firebase_credentials.values()):
    raise RuntimeError("Firebase credentials are not properly configured!")

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Load API key from environment variables
API_KEY = os.getenv("CERT_API_KEY")
if not API_KEY:
    raise RuntimeError("API key not configured properly!")

# Data model for certificate generation requests
class CertificateRequest(BaseModel):
    username: str
    certificate_id: str
    from_date: str
    to_date: str

# Helper function: Cleanup generated files
def file_cleanup(file_path: str):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Deleted file: {file_path}")
    except Exception as e:
        logging.error(f"Error deleting file {file_path}: {str(e)}")

# List of email IDs to exclude from cleanup
EXCLUDED_EMAILS = ["root@mathin"]

# Cleanup old user entries
def cleanup_old_user_entries():
    try:
        current_time = datetime.now(timezone.utc)
        cutoff_time = current_time - timedelta(hours=24)
        logging.info(f"Current UTC time: {current_time}, Cutoff time: {cutoff_time}")

        user_entries = db.collection("userEntries").get()
        logging.info(f"Total user entries fetched: {len(user_entries)}")

        for entry in user_entries:
            data = entry.to_dict()
            logging.info(f"Processing entry ID: {entry.id}, Data: {data}")

            # Skip if the email is in the excluded list
            if "email" in data and data["email"] in EXCLUDED_EMAILS:
                logging.info(f"Skipping cleanup for email: {data['email']}")
                continue
            if "lastEntry" in data:
                last_entry_time = data["lastEntry"]
                logging.info(f"Last entry time: {last_entry_time}")
                if last_entry_time < cutoff_time:
                    db.collection("userEntries").document(entry.id).delete()
                    logging.info(f"Deleted user entry: {entry.id}")
                else:
                    logging.info(f"Entry {entry.id} is not older than 24 hours.")
            else:
                logging.warning(f"Entry {entry.id} has no 'lastEntry' field.")
    except Exception as e:
        logging.error(f"Error during user entries cleanup: {str(e)}")

# Cleanup expired pass entries
def cleanup_expired_pass_entries():
    try:
        current_time = datetime.now(timezone.utc)
        logging.info(f"Current UTC time: {current_time}")

        pass_entries = db.collection("passEntries").get()
        logging.info(f"Total pass entries fetched: {len(pass_entries)}")

        for entry in pass_entries:
            data = entry.to_dict()
            logging.info(f"Processing entry ID: {entry.id}, Data: {data}")

            # Skip if the email is in the excluded list
            if "email" in data and data["email"] in EXCLUDED_EMAILS:
                logging.info(f"Skipping cleanup for email: {data['email']}")
                continue
            if "expiryTimestamp" in data:
                expiry_time = data["expiryTimestamp"]
                logging.info(f"Expiry time: {expiry_time}")
                if expiry_time < current_time:
                    db.collection("passEntries").document(entry.id).delete()
                    logging.info(f"Deleted pass entry: {entry.id}")
                else:
                    logging.info(f"Entry {entry.id} is not expired.")
            else:
                logging.warning(f"Entry {entry.id} has no 'expiryTimestamp' field.")
    except Exception as e:
        logging.error(f"Error during pass entries cleanup: {str(e)}")

@app.get("/cleanup")
async def trigger_cleanup(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        logging.warning("Unauthorized access attempt with invalid API key!")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key!")

    try:
        cleanup_old_user_entries()
        cleanup_expired_pass_entries()
        logging.info("Cleanup tasks executed successfully!")
        return {"status": "success", "message": "Cleanup tasks executed successfully!"}

    except Exception as e:
        logging.error(f"Error during cleanup execution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "MathIn-CertAPI is healthy and running!"}

@app.post("/generate-certificate")
async def generate_certificate(
    data: CertificateRequest,
    background_tasks: BackgroundTasks,
    x_api_key: str = Header(None),
):
    if x_api_key != API_KEY:
        logging.warning("Unauthorized access attempt with invalid API key!")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key!")

    try:
        os.makedirs("generatedCertificates", exist_ok=True)
        output_file = os.path.join("generatedCertificates", f"{data.certificate_id}_certificate.pdf")

        await generateCertificate(
            USERNAME_INPUT=data.username,
            CERTIFICATE_ID=data.certificate_id,
            FROM_DATE=data.from_date,
            TO_DATE=data.to_date,
            OUTPUT_FILE=output_file,
        )

        if not os.path.exists(output_file):
            logging.error("Certificate file not found after generation!")
            raise HTTPException(status_code=500, detail="Expected certificate file not found!")

        background_tasks.add_task(file_cleanup, output_file)
        logging.info(f"Certificate generated successfully: {output_file}")
        return FileResponse(
            path=output_file,
            media_type="application/pdf",
            filename=f"{data.certificate_id}_certificate.pdf"
        )

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")