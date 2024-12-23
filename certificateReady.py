# certificateReady.py

import io
import os
import qrcode
from PIL import Image, ImageDraw
from PyPDF2 import PdfReader, PdfWriter, PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

async def generateCertificate(USERNAME_INPUT="User Name", CERTIFICATE_ID="XXXXXXXXXXXXXXXX", FROM_DATE="dd-mm-yyyy", TO_DATE="DD-MM-YYYY", OUTPUT_FILE="XXXXXXXXXXXXXXXX_certificate.pdf"):
  
  # Function for username alignment
  def username_Alignment(text, max_chars_per_line):
    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
      if len(current_line) + len(word) + 1 <= max_chars_per_line:
        if current_line:
          current_line += " "
        current_line += word
      else:
        lines.append(current_line)
        current_line = word

    if current_line:
      lines.append(current_line)

    return lines

  # Function for username overlay
  def username_Overlay(input_pdf_path, output_pdf_path, username):
    username = (username[:33]).strip()
    x, y = 390, 329
    max_chars_per_line = 16

    if len(username) <= 8:
      font_size = 50
      line_spacing = 58
    elif len(username) in range(9, 17):
      font_size = 38
      line_spacing = 48
    elif len(username) in range(17, 25):
      font_size = 40
      line_spacing = 48
    else:
      font_size = 30
      line_spacing = 48

    lines = username_Alignment(username, max_chars_per_line)

    if len(lines) >= 3:
      line_spacing = 40

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    pdfmetrics.registerFont(TTFont("RobotoMono-Bold", "fonts/RobotoMono-Bold.ttf"))
    font_name = "RobotoMono-Bold"
    can.setFont(font_name, font_size)
    can.setFillColor("#ababab")
    char_width = can.stringWidth("M", font_name, font_size)
    start_y = y + (len(lines) - 1) * line_spacing / 2

    for i, line in enumerate(lines):
      current_x = x - (char_width * len(line)) / 2
      current_y = start_y - i * line_spacing
      can.drawString(current_x, current_y, line)

    can.save()
    packet.seek(0)
    overlay_pdf = PdfReader(packet)
    original_pdf = PdfReader(input_pdf_path)
    pdf_writer = PdfWriter()

    for page_num in range(len(original_pdf.pages)):
      page = original_pdf.pages[page_num]
      overlay_page = overlay_pdf.pages[0]
      page.merge_page(overlay_page)
      pdf_writer.add_page(page)

    with open(output_pdf_path, "wb") as output_file:
      pdf_writer.write(output_file)

  # Function for certificate ID overlay
  def certificateId_Overlay(input_pdf_path, output_pdf_path, certificate_id):
    x, y = 613, 362
    page_number = 0
    char_spacing = 1
    font_path = "fonts/RobotoMono-SemiBold.ttf"
    font_name = "RobotoMono"

    pdfmetrics.registerFont(TTFont(font_name, font_path))
    pdf_reader = PdfReader(input_pdf_path)

    if page_number < 0 or page_number >= len(pdf_reader.pages):
      raise ValueError("Page number out of range.")

    original_page = pdf_reader.pages[page_number]
    page_width = original_page.mediabox.width
    page_height = original_page.mediabox.height
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    can.setFont(font_name, 14)
    can.setFillColor(HexColor("#F9F7F7"))

    current_x = x
    for char in certificate_id:
      can.drawString(current_x, y, char)
      current_x += char_spacing * 10

    can.save()
    packet.seek(0)
    overlay_pdf_reader = PdfReader(packet)
    overlay_page = overlay_pdf_reader.pages[0]

    combined_page = PageObject.create_blank_page(width=page_width, height=page_height)
    combined_page.merge_page(original_page)
    combined_page.merge_page(overlay_page)

    pdf_writer = PdfWriter()
    for i, page in enumerate(pdf_reader.pages):
      if i == page_number:
        pdf_writer.add_page(combined_page)
      else:
        pdf_writer.add_page(page)

    with open(output_pdf_path, "wb") as output_file:
      pdf_writer.write(output_file)

  # Function for QR code generation and overlay
  def generateQR_Overlay(input_pdf_path, output_pdf_path, certificate_id):
    foreground_color = "#1EBB58"
    background_color = "#18181B"
    qr_data = "https://aswin-vs.github.io/MathIn/verify/" + certificate_id
    x = 638.6
    y = 184
    qr_gen_size = 960
    qr_size = 96

    qr = qrcode.QRCode(border=0)
    qr.add_data(qr_data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    matrix_size = len(matrix)
    module_size = qr_gen_size / matrix_size
    qr_image = Image.new("RGB", (qr_gen_size, qr_gen_size), background_color)
    draw = ImageDraw.Draw(qr_image)

    for y_index, row in enumerate(matrix):
      for x_index, cell in enumerate(row):
        if cell:
          draw.rectangle(
            (
              x_index * module_size,
              y_index * module_size,
              (x_index + 1) * module_size,
              (y_index + 1) * module_size,
            ),
            fill=foreground_color,
          )

    qr_image_bytes = io.BytesIO()
    qr_image.save(qr_image_bytes, format="PNG")
    qr_image_bytes.seek(0)
    qr_image_reader = ImageReader(qr_image_bytes)
    pdf_reader = PdfReader(input_pdf_path)
    pdf_writer = PdfWriter()

    for page_num in range(len(pdf_reader.pages)):
      pdf_page = pdf_reader.pages[page_num]
      page_width = float(pdf_page.mediabox.width)
      page_height = float(pdf_page.mediabox.height)
      packet = io.BytesIO()
      can = canvas.Canvas(packet, pagesize=(page_width, page_height))
      can.drawImage(qr_image_reader, x=x, y=y, width=qr_size, height=qr_size)
      can.save()
      packet.seek(0)
      overlay_pdf = PdfReader(packet)
      overlay_page = overlay_pdf.pages[0]
      new_page = PageObject.create_blank_page(width=page_width, height=page_height)
      new_page.merge_page(pdf_page)
      new_page.merge_page(overlay_page)
      pdf_writer.add_page(new_page)

    with open(output_pdf_path, 'wb') as output_pdf:
      pdf_writer.write(output_pdf)

  # Function for validity overlay
  def validity_Overlay(input_pdf_path, output_pdf_path, from_date, to_date):
    x, y = 230, 107.5
    page_number = 0
    char_spacing = 1.3
    font_path = "fonts/RobotoMono-Bold.ttf"
    font_name = "RobotoMono"
    validity_date = from_date + " to " + to_date

    pdfmetrics.registerFont(TTFont(font_name, font_path))
    pdf_reader = PdfReader(input_pdf_path)
    original_page = pdf_reader.pages[page_number]
    page_width = original_page.mediabox.width
    page_height = original_page.mediabox.height
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    can.setFont(font_name, 23)
    can.setFillColor(HexColor("#1EBB58"))

    current_x = x
    for char in validity_date:
      can.drawString(current_x, y, char)
      current_x += char_spacing * 10

    can.save()
    packet.seek(0)
    overlay_pdf_reader = PdfReader(packet)
    overlay_page = overlay_pdf_reader.pages[0]
    combined_page = PageObject.create_blank_page(width=page_width, height=page_height)
    combined_page.merge_page(original_page)
    combined_page.merge_page(overlay_page)

    pdf_writer = PdfWriter()
    for i, page in enumerate(pdf_reader.pages):
      if i == page_number:
        pdf_writer.add_page(combined_page)
      else:
        pdf_writer.add_page(page)

    with open(output_pdf_path, "wb") as output_file:
      pdf_writer.write(output_file)

  # Function for verification URL overlay
  def verify_Overlay(input_pdf_path, output_pdf_path, certificate_id):
    x, y = 260, 42.8
    page_number = 0
    font_path = "fonts/RobotoMono-SemiBold.ttf"
    font_name = "RobotoMono"
    font_size = 13
    url = "https://aswin-vs.github.io/MathIn/verify/" + certificate_id

    pdfmetrics.registerFont(TTFont(font_name, font_path))
    buffer = 10
    url_width = stringWidth(url, font_name, font_size) + buffer

    pdf_reader = PdfReader(input_pdf_path)
    original_page = pdf_reader.pages[page_number]
    page_width = original_page.mediabox.width
    page_height = original_page.mediabox.height
    packet = io.BytesIO()

    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
    can.setFont(font_name, font_size)
    can.setFillColor(HexColor("#F9F7F7"))
    can.linkURL(url, (x, y - 5, x + url_width, y + 20), relative=1)
    can.drawString(x, y, url)
    can.save()

    packet.seek(0)
    overlay_pdf_reader = PdfReader(packet)
    overlay_page = overlay_pdf_reader.pages[0]
    combined_page = PageObject.create_blank_page(width=page_width, height=page_height)
    combined_page.merge_page(original_page)
    combined_page.merge_page(overlay_page)

    pdf_writer = PdfWriter()
    for i, page in enumerate(pdf_reader.pages):
      if i == page_number:
        pdf_writer.add_page(combined_page)
      else:
        pdf_writer.add_page(page)

    with open(output_pdf_path, "wb") as output_file:
      pdf_writer.write(output_file)
  
  # Function for PDF Metadata update
  def update_Pdf_Metadata(input_pdf_path, output_pdf_path, title, author, subject):
    try:
      reader = PdfReader(input_pdf_path)
      writer = PdfWriter()
      for page in reader.pages:
        writer.add_page(page)

      metadata = {'/Title': title}
    
      if author:
        metadata['/Author'] = author
    
      if subject:
        metadata['/Subject'] = subject
    
      writer.add_metadata(metadata)
      with open(output_pdf_path, "wb") as f:
        writer.write(f)

    except Exception as e:
      print(f"Error updating pdf metadata: {e} !")
  
  INPUT_FILE = "certificateTemplate.pdf"
  OUTPUT_FILE = OUTPUT_FILE

  if not os.path.exists(INPUT_FILE):
    raise FileNotFoundError(f"Template file '{INPUT_FILE}' not found !")

  try:
    username_Overlay(INPUT_FILE, OUTPUT_FILE, USERNAME_INPUT)
    certificateId_Overlay(OUTPUT_FILE, OUTPUT_FILE, CERTIFICATE_ID)
    generateQR_Overlay(OUTPUT_FILE, OUTPUT_FILE, CERTIFICATE_ID)
    validity_Overlay(OUTPUT_FILE, OUTPUT_FILE, FROM_DATE, TO_DATE)
    verify_Overlay(OUTPUT_FILE, OUTPUT_FILE, CERTIFICATE_ID)
    update_Pdf_Metadata(OUTPUT_FILE, OUTPUT_FILE, title="MathIn Pro - Certificate", author="MathIn", subject="Certificate for successful completion of MathIn Pro test")

    return OUTPUT_FILE
  
  except Exception as e:
    print(e)
    raise RuntimeError(f"Error with 'generateCertificate' function !")
