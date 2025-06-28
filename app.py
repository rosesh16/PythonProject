from flask import Flask, request, jsonify, send_from_directory, send_file, render_template_string
from PyPDF2 import PdfReader
from gtts import gTTS
import os
import uuid
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
MEDIA_FOLDER = 'media'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# === ✅ REST API Endpoint ===
@app.route('/api/convert', methods=['POST'])
def convert_pdf_to_speech():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No PDF file uploaded.'}), 400

    pdf_file = request.files['pdf']
    page = request.form.get('page')
    read_full = request.form.get('read_full', 'false').lower() == 'true'

    unique_pdf_name = f"{uuid.uuid4().hex}_{pdf_file.filename}"
    pdf_path = os.path.join(UPLOAD_FOLDER, unique_pdf_name)
    pdf_file.save(pdf_path)

    try:
        reader = PdfReader(pdf_path)
        text = ""

        if read_full:
            for pg in reader.pages:
                pg_text = pg.extract_text()
                if pg_text:
                    text += pg_text + "\n"
        else:
            if not page:
                return jsonify({'error': 'Page number is required if not reading full PDF.'}), 400

            page_num = int(page) - 1
            if page_num < 0 or page_num >= len(reader.pages):
                return jsonify({'error': 'Page number out of range.'}), 400

            text = reader.pages[page_num].extract_text() or ""

        if not text.strip():
            return jsonify({'error': 'No readable text found in PDF.'}), 400

        audio_filename = f"{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join(MEDIA_FOLDER, audio_filename)
        tts = gTTS(text=text, lang='en')
        tts.save(audio_path)

        # Return response as HTML with audio + download
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Audio Generated</title>
                <style>
                    body { font-family: Arial; background: #f0f0f0; padding: 30px; text-align: center; }
                    .card {
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        display: inline-block;
                        box-shadow: 0 0 15px rgba(0,0,0,0.1);
                    }
                    audio { margin-top: 20px; width: 100%; }
                    a.button {
                        display: inline-block;
                        margin-top: 20px;
                        padding: 10px 20px;
                        background: #007bff;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <h2>✅ Audio Generated Successfully</h2>
                    <audio controls autoplay>
                        <source src="/media/{{ filename }}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio><br>
                    <a class="button" href="/media/{{ filename }}" download>⬇ Download MP3</a>
                    <br><br>
                    <a href="/">🔙 Upload Another PDF</a>
                </div>
            </body>
            </html>
        ''', filename=audio_filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


# === ✅ Force file download when accessed directly ===
@app.route('/media/<filename>')
def serve_audio(filename):
    audio_path = os.path.join(MEDIA_FOLDER, filename)
    return send_file(audio_path, as_attachment=False)  # Set to True to always force download


# === ✅ Simple Form Frontend ===
@app.route('/', methods=['GET'])
def upload_form():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>PDF to Speech</title>
        <style>
            body { font-family: Arial; background: #e9ecef; padding: 40px; }
            .container {
                background: white;
                max-width: 500px;
                margin: auto;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h2 { text-align: center; }
            input[type="submit"] {
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                width: 100%;
                margin-top: 15px;
                cursor: pointer;
            }
            label, input, select {
                width: 100%;
                margin-top: 10px;
                font-size: 1rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔊 PDF to Audio Converter</h2>
            <form action="/api/convert" method="post" enctype="multipart/form-data">
                <label>Upload PDF:</label>
                <input type="file" name="pdf" required>

                <label>Page number (optional):</label>
                <input type="number" name="page" min="1">

                <label><input type="checkbox" name="read_full" value="true"> Read entire PDF</label>

                <input type="submit" value="Convert to Speech">
            </form>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True)
