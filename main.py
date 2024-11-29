from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from certificateReady import generateCertificate
from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

API_KEY = os.getenv("CERT_API_KEY")
if not API_KEY:
  raise RuntimeError("API key is not configured properly !")

class CertificateRequest(BaseModel):
  username: str
  certificate_id: str
  from_date: str
  to_date: str

@app.middleware("http")
async def ip_restriction_middleware(request: Request, call_next):
  allowed_hosts = {"localhost", "127.0.0.1", "*"}
  client_host = request.client.host
  host_header = request.headers.get("host", "")

  try:
    if request.url.path == "/health":
      return await call_next(request)

    if client_host not in allowed_hosts and not any(host in host_header for host in allowed_hosts):
      raise HTTPException(status_code=403, detail="Access forbidden: Unauthorized host IP !")
    
    return await call_next(request)

  except HTTPException as e:
    return JSONResponse(status_code=e.status_code, content={"Detail": e.detail})
  except Exception as e:
    return JSONResponse(status_code=500, content={"Detail": f"Internal server error: {str(e)} !"})

@app.get("/health")
async def health_check():
  return {"status": "ok"}

@app.post("/generate-certificate/")
async def generate_certificate_endpoint(
  data: CertificateRequest,
  x_api_key: str = Header(...),
):
  
  if x_api_key != API_KEY:
    raise HTTPException(status_code=401, detail="Unauthorized: Invalid API key !")

  output_file = f"{data.certificate_id}_certificate.pdf"

  try:
    await generateCertificate(
      USERNAME_INPUT=data.username,
      CERTIFICATE_ID=data.certificate_id,
      FROM_DATE=data.from_date,
      TO_DATE=data.to_date,
      OUTPUT_FILE=output_file
    )

    if not os.path.exists(output_file):
      raise HTTPException(status_code=500, detail="Certificate generation failed !")

    return FileResponse(
      output_file,
      media_type="application/pdf",
      filename=f"certificate_{data.certificate_id}.pdf",
    )

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error generating certificate: {str(e)} !")
  
  finally:
    try:
      if os.path.exists(output_file):
        os.remove(output_file)
    except Exception as e:
      raise HTTPException(status_code=500, detail=f"Error removing used files: {str(e)} !")