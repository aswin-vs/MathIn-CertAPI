from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from certificateReady import generateCertificate
import os

app = FastAPI()

API_KEY_ENV = "CERT_API_KEY"
TEMPLATE_PATH = "certificateTemplate.pdf"

class CertificateRequest(BaseModel):
  username: str
  certificate_id: str
  from_date: str
  to_date: str

@app.get("/health")
async def health_check():
  return {"status": "ok"}

@app.post("/generate-certificate/")
async def generate_certificate(
  data: CertificateRequest,
  x_api_key: str = Header(default=None)
):
  # Validate the API key
  expected_api_key = os.getenv(API_KEY_ENV)
  if not expected_api_key or x_api_key != expected_api_key:
    raise HTTPException(status_code=401, detail="Invalid or missing API key.")

  # Create a unique output file based on certificate_id
  output_file = f"certificateOutput_{data.certificate_id}.pdf"

  try:
    # Generate the certificate
    generateCertificate(
      TEMPLATE_PATH=TEMPLATE_PATH,
      USERNAME_INPUT=data.username,
      CERTIFICATE_ID=data.certificate_id,
      FROM_DATE=data.from_date,
      TO_DATE=data.to_date
    )

    # Ensure the generated file exists
    if not os.path.exists(output_file):
      raise HTTPException(status_code=500, detail="Certificate generation failed.")

    # Return the PDF as a response
    response = FileResponse(
      output_file,
      media_type="application/pdf",
      filename="certificate.pdf"
    )

    # Cleanup the generated file after the response is sent
    @response.background
    def cleanup():
      if os.path.exists(output_file):
        os.remove(output_file)

    return response

  except Exception as e:
    # Clean up the file in case of any errors
    if os.path.exists(output_file):
      os.remove(output_file)
    raise HTTPException(status_code=500, detail=f"Error generating certificate: {str(e)}")