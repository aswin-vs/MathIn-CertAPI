# main.py

import os
from fastapi import FastAPI, HTTPException, Header
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

@app.post("/generate-certificate/")
async def generate_certificate(data: CertificateRequest, x_api_key: str = Header(None)):

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
      raise HTTPException(status_code=500, detail="Certificate generation failed !")

    return {"message": "Certificate generated successfully !", "file_path": output_file}

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Internal server error !")

@app.get("/viewcertificates")
async def view_certificates():
  folder = "generatedCertificates"
  
  # Ensure the folder exists
  if not os.path.exists(folder):
    return {"message": "No certificates folder found.", "files": []}
  
  # List files in the folder
  try:
    files = [f for f in os.listdir(folder) if f.endswith(".pdf")]
    return {"message": "Certificates found.", "files": files}
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error reading folder: {str(e)}")