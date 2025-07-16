import os
import logging
import PyPDF2
import docx
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF file
    """
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {str(e)}")
        return ""

def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from DOCX file
    """
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {str(e)}")
        return ""

def process_cv_file(file_path: str, filename: str) -> str:
    """
    Process uploaded CV file and extract text content
    """
    try:
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        if file_extension == 'pdf':
            return extract_text_from_pdf(file_path)
        elif file_extension in ['docx', 'doc']:
            return extract_text_from_docx(file_path)
        else:
            logging.error(f"Unsupported file format: {file_extension}")
            return ""
            
    except Exception as e:
        logging.error(f"Error processing CV file: {str(e)}")
        return ""

def save_uploaded_file(file, upload_folder: str) -> tuple:
    """
    Save uploaded file and return (success, filename, file_path)
    """
    try:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to avoid conflicts
            timestamp = str(int(os.path.getmtime(__file__) * 1000))
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{timestamp}{ext}"
            
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            
            return True, filename, file_path
        else:
            return False, None, None
            
    except Exception as e:
        logging.error(f"Error saving uploaded file: {str(e)}")
        return False, None, None
