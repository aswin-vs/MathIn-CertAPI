import os
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from certificateReady import generateCertificate

# Retrieve API key from environment variables
API_KEY = os.getenv("CERT_API_KEY")
if not API_KEY:
  raise RuntimeError("API key not configured properly!")

# Create FastAPI app
app = FastAPI()

# Define the request model
class CertificateRequest(BaseModel):
  username: str
  certificate_id: str
  from_date: str
  to_date: str

# Health check endpoint
@app.get("/health")
async def health_check():
  return {"status": "ok", "message": "MathIn-CertAPI is healthy and running!"}

# Cleanup logic for temporary files
def file_cleanup(file_path: str):
  try:
    if os.path.exists(file_path):
      os.remove(file_path)
      print(f"Deleted file: {file_path}")
  except Exception as e:
    print(f"Error deleting file {file_path}: {str(e)}")

# Generate certificate endpoint
@app.post("/generate-certificate/")
async def generate_certificate(data: CertificateRequest, x_api_key: str = Header(None)):

  # Check API key
  if x_api_key != API_KEY:
    raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key!")

  try:
    # Create directory for certificates if it doesn't exist
    os.makedirs("generatedCertificates", exist_ok=True)

    # Define output file path
    output_file = os.path.join("generatedCertificates", f"{data.certificate_id}_certificate.pdf")

    # Call generateCertificate function
    await generateCertificate(
      USERNAME_INPUT=data.username,
      CERTIFICATE_ID=data.certificate_id,
      FROM_DATE=data.from_date,
      TO_DATE=data.to_date,
      OUTPUT_FILE=output_file,
    )

    # Verify the file was created
    if not os.path.exists(output_file):
      raise HTTPException(status_code=500, detail="Certificate generation failed! File not found.")

    # Use FastAPI's dependency injection to handle file cleanup after the response
    return FileResponse(
      path=output_file,
      media_type="application/pdf",
      filename=f"{data.certificate_id}_certificate.pdf",
      background=Depends(lambda: file_cleanup(output_file))
    )

  except HTTPException:
    raise  # Re-raise known HTTP exceptions
  except Exception as e:
    # Log the exact error for debugging
    print(f"Unexpected error: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")