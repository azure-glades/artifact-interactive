import uuid
import json
import os
import io
import base64
import qrcode
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
# Note: Database imports are relative, relying on database.py
from database import init_db, store_label_data, get_label_data, get_all_label_summaries, delete_label_data
from werkzeug.utils import secure_filename

# --- Configuration ---
UPLOADS_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav'}

app = Flask(__name__)
app.config['UPLOADS_FOLDER'] = UPLOADS_FOLDER
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# Initialize the database when the app starts
init_db(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------------------
# 2. File Upload Handling (No changes needed here, keeping for context)
# ----------------------------------------------------
@app.route('/api/upload', methods=['POST'])
def upload_file():
    # ... (existing file upload logic)
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOADS_FOLDER'], unique_filename)
        
        try:
            file.save(filepath)
            # print(f"SUCCESS: File saved to {os.path.abspath(filepath)}") # Existing log is helpful
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to save file at path {os.path.abspath(filepath)}. Error: {e}") 
            return jsonify({"error": f"Server-side failure saving file: {e}"}), 500
        
        return jsonify({
            "success": True, 
            "filename": unique_filename,
            "media_uri": url_for('uploaded_file', filename=unique_filename) 
        }), 200
    else:
        return jsonify({"error": "File type not allowed"}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOADS_FOLDER'], filename)

# ----------------------------------------------------
# 3. Data Submission & Storage (Receiving JSON)
# ----------------------------------------------------
@app.route('/api/create_label', methods=['POST'])
def create_label():
    """Receives JSON data, stores it, and returns the unique URL."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided in request body."}), 400

        label_id = str(uuid.uuid4())[:8]

        # CRITICAL STEP: Call the function that tries to write to the DB
        store_label_data(label_id, data) 

        label_url = url_for('unified_exhibit_site', label_id=label_id)

        print(f"--- SUCCESS: Label {label_id} created. URL: {label_url} ---")
        return jsonify({
            "message": "Exhibit label data successfully saved.",
            "label_id": label_id,
            "url": label_url
        }), 201

    except Exception as e:
        print(f"ERROR during label creation (likely DB issue): {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500
        
# ----------------------------------------------------
# 4. Label Deletion and QR Code Generation (Keeping existing logic)
# ----------------------------------------------------
@app.route('/api/delete_label/<label_id>', methods=['DELETE'])
def delete_label(label_id):
    success = delete_label_data(label_id)
    if success:
        return jsonify({"message": f"Label {label_id} deleted successfully."}), 200
    else:
        return jsonify({"error": f"Could not delete label {label_id}."}), 404

def generate_qrcode_base64(url):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_b64}"

# ----------------------------------------------------
# 5. Unified Site Structure (The New Viewer)
# ----------------------------------------------------
@app.route('/exhibit/<label_id>')
def unified_exhibit_site(label_id):
    label_data = get_label_data(label_id) # This is the failed fetch call
    
    if not label_data:
        # Returns the 404 error you saw
        return render_template('error_404.html', label_id=label_id), 404

    all_exhibits = get_all_label_summaries()
    full_url = url_for('unified_exhibit_site', label_id=label_id, _external=True)
    qr_code_image = generate_qrcode_base64(full_url)
    template_type = label_data.get('template', 'minimalist')
    
    return render_template(
        'base_site.html',
        all_exhibits=all_exhibits,
        current_exhibit=label_data,
        current_template=f'{template_type}_label.html',
        qr_code_image=qr_code_image
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error_404.html', label_id='N/A'), 404


if __name__ == '__main__':
    app.run(debug=True)