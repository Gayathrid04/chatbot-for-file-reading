from flask import Flask, request, jsonify, render_template
import os
import io
import PyPDF2
import pandas as pd
from docx import Document
import ollama  # Using Ollama's functional interface

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')  # Ensure index.html is in the "templates" folder

# Function to process PDF documents using a BytesIO stream
def process_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as f:
        pdf_bytes = f.read()
    pdf_stream = io.BytesIO(pdf_bytes)
    reader = PyPDF2.PdfReader(pdf_stream)
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# Function to process Word documents
def process_word(file_path):
    doc = Document(file_path)
    return ' '.join([p.text for p in doc.paragraphs])

# Function to process Excel documents
def process_excel(file_path):
    df = pd.read_excel(file_path)
    return df.to_string()

# Endpoint for file uploading and processing.
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    model_name = request.form.get('model', '')
    file_path = os.path.join('./', file.filename)
    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({'error': f'Could not save file: {str(e)}'}), 500

    f_lower = file.filename.lower()
    if f_lower.endswith('.pdf'):
        content = process_pdf(file_path)
    elif f_lower.endswith('.docx'):
        content = process_word(file_path)
    elif f_lower.endswith('.xlsx'):
        content = process_excel(file_path)
    else:
        os.remove(file_path)
        return jsonify({'error': 'Unsupported file format'}), 400

    try:
        os.remove(file_path)
    except Exception as e:
        print(f"Warning: unable to delete file {file_path}: {e}")
    return jsonify({'content': content, 'model': model_name})

# Endpoint for querying the processed file content using the selected model.
@app.route('/query', methods=['POST'])
def query_content():
    data = request.get_json()
    content = data.get('content', '')
    question = data.get('question', '')
    model_name = data.get('model', '')

    if model_name == "Gemma 7B":
        selected_model = "gemma-7b"
    elif model_name == "Gemma 2B":
        selected_model = "gemma-2b"
    elif model_name == "Llama3":
        selected_model = "llama3"
    else:
        return jsonify({'error': f'Model "{model_name}" not recognized'}), 400

    try:
        prompt = content + "\n\n" + question
        # Generate a response using the functional interface.
        generate_response = ollama.generate(model=selected_model, prompt=prompt)
        # Convert the response to string so that it's JSON serializable.
        response_text = str(generate_response)
        return jsonify({'response': response_text})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
