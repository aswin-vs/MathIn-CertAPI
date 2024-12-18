# main.py

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

app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

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

API_KEY = os.getenv("CERT_API_KEY")
if not API_KEY:
  raise RuntimeError("API key not configured properly!")

class CertificateRequest(BaseModel):
  username: str
  certificate_id: str
  from_date: str
  to_date: str

def file_cleanup(file_path: str):
  try:
    if os.path.exists(file_path):
      os.remove(file_path)
      logging.info(f"Deleted file: {file_path}")
  except Exception as e:
    logging.error(f"Error deleting file {file_path}: {str(e)}")

def cleanup_old_user_entries():
  try:
    current_time = datetime.now(timezone.utc)
    cutoff_time = current_time - timedelta(hours=24)
    user_entries = db.collection("userEntries").get()

    for entry in user_entries:
      data = entry.to_dict()
      if "lastEntry" in data:
        last_entry_time = data["lastEntry"].replace(tzinfo=None)
        if last_entry_time < cutoff_time:
          db.collection("userEntries").document(entry.id).delete()
          logging.info(f"Deleted user entry: {entry.id}")

  except Exception as e:
    logging.error(f"Error during user entries cleanup: {str(e)}")

def cleanup_expired_pass_entries():
  try:
    current_time = datetime.now(timezone.utc)
    pass_entries = db.collection("passEntries").get()

    for entry in pass_entries:
      data = entry.to_dict()
      if "expiryTimestamp" in data:
        expiry_time = data["expiryTimestamp"].replace(tzinfo=None)
        if expiry_time < current_time:
          db.collection("passEntries").document(entry.id).delete()
          logging.info(f"Deleted pass entry: {entry.id}")

  except Exception as e:
    logging.error(f"Error during pass entries cleanup: {str(e)}")

@app.get("/cleanup")
async def trigger_cleanup(x_api_key: str = Header(None)):
  if x_api_key != API_KEY:
    logging.warning("Unauthorized access attempt with invalid API key !")
    raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key !")

  try:
    cleanup_old_user_entries()
    cleanup_expired_pass_entries()
    logging.info("Cleanup tasks executed successfully !")
    return {"status": "success", "message": "Cleanup tasks executed successfully !"}

  except Exception as e:
    logging.error(f"Error during cleanup execution: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
  return {"status": "ok", "message": "MathIn-CertAPI is healthy and running !"}

@app.post("/generate-certificate")
async def generate_certificate(
  data: CertificateRequest,
  background_tasks: BackgroundTasks,
  x_api_key: str = Header(None),
):
  if x_api_key != API_KEY:
    logging.warning("Unauthorized access attempt with invalid API key !")
    raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key !")

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
      logging.error("Certificate file not found after generation !")
      raise HTTPException(status_code=500, detail="Expected certificate file not found !")

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