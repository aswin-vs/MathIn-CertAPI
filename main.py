# main.py

import os
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from certificateReady import generateCertificate

# from dotenv import load_dotenv
# load_dotenv()
API_KEY = os.getenv("CERT_API_KEY")
if not API_KEY:
  raise RuntimeError("API key not configured properly !")

app = FastAPI()

class CertificateRequest(BaseModel):
  username: str
  certificate_id: str
  from_date: str
  to_date: str

@app.get("/health")
async def health_check():
  return {"status": "ok", "message": "MathIn-CertAPI is healthy and running !"}

def file_cleanup(file_path: str):
  try:
    if os.path.exists(file_path):
      os.remove(file_path)
      print(f"Deleted file: {file_path}")
  except Exception as e:
    print(f"Error deleting file {file_path}: {str(e)}")

@app.post("/generate-certificate")
async def generate_certificate(
  data: CertificateRequest,
  background_tasks: BackgroundTasks,
  x_api_key: str = Header(None)
):

  if x_api_key != API_KEY:
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
      raise HTTPException(status_code=500, detail="Expected certificate file not found !")

    # Schedule the file cleanup task
    background_tasks.add_task(file_cleanup, output_file)

    return FileResponse(
      path=output_file,
      media_type="application/pdf",
      filename=f"{data.certificate_id}_certificate.pdf"
    )

  except HTTPException:
    raise  
  except Exception as e:
    print(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")