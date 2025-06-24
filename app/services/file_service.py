"""
Service functions for file handling (validation, naming, uploads).
"""
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app

def allowed_file(filename, allowed_extensions):
    """
    Checks if the uploaded file has an allowed extension.

    Args:
        filename (str): The name of the file.
        allowed_extensions (set): Set of allowed extensions.

    Returns:
        bool: True if the file extension is allowed, False otherwise.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def generate_unique_filename(original_filename):
    """Gera um nome único para o arquivo mantendo a extensão"""
    name, ext = os.path.splitext(original_filename)
    return f"{uuid.uuid4().hex}{ext}"
