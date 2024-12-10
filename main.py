import os
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from certificateReady import generateCertificate

API_KEY = os.getenv("CERT_API_KEY")
if not API_KEY:
  raise RuntimeError("API key not configured properly!")

app = FastAPI()

class CertificateRequest(BaseModel):
  username: str
  certificate_id: str
  from_date: str
  to_date: str

@app.get("/health")
async def health_check():
  return {"status": "ok", "message": "MathIn-CertAPI is healthy and running!"}

@app.post("/generate-certificate/")
async def generate_certificate(data: CertificateRequest, x_api_key: str = Header(None)):
  if x_api_key != API_KEY:
    raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key!")

  try:
    # Ensure the output directory exists
    os.makedirs("generatedCertificates", exist_ok=True)
    output_file = os.path.join("generatedCertificates", f"{data.certificate_id}_certificate.pdf")

    # Generate the certificate
    await generateCertificate(
      USERNAME_INPUT=data.username,
      CERTIFICATE_ID=data.certificate_id,
      FROM_DATE=data.from_date,
      TO_DATE=data.to_date,
      OUTPUT_FILE=output_file,
    )

    # Check if the file was created successfully
    if not os.path.exists(output_file):
      raise HTTPException(status_code=500, detail="Certificate generation failed!")

    # Send the file as a response
    response = FileResponse(
      path=output_file,
      media_type="application/pdf",
      filename=f"{data.certificate_id}_certificate.pdf",
    )

    # Cleanup: Delete the file after sending it
    @response.call_on_close
    def cleanup():
      try:
        os.remove(output_file)
      except Exception as e:
        print(f"Error deleting file {output_file}: {str(e)}")

    return response

  except Exception as e:
    print(f"Internal Server Error: {str(e)}")
    raise HTTPException(status_code=500, detail="Internal server error!")
