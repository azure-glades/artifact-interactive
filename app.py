import uuid
import json
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
from database import init_db, store_label_data, get_label_data, get_all_label_summaries
from werkzeug.utils import secure_filename

# --- Configuration ---
UPLOADS_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav'}

app = Flask(__name__)
app.config['UPLOADS_FOLDER'] = UPLOADS_FOLDER
# Ensure the upload directory exists
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# Initialize the database when the app starts
init_db(app)

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------------------
# 1. Frontend Route (Serving the index.html form)
# ----------------------------------------------------
@app.route('/')
def home():
    """Renders the data collection form."""
    return render_template('index.html')

# ----------------------------------------------------
# 2. File Upload Handling
# ----------------------------------------------------
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handles image and audio file uploads."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        # Use secure_filename to prevent directory traversal attacks
        filename = secure_filename(file.filename)
        # Prepend UUID to filename to ensure uniqueness
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOADS_FOLDER'], unique_filename)
        
        file.save(filepath)
        
        # Return the server-side file path to the frontend for use in the exhibit data
        return jsonify({
            "success": True, 
            "filename": unique_filename,
            # The URI the final label will use to access the file
            "media_uri": url_for('uploaded_file', filename=unique_filename) 
        }), 200
    else:
        return jsonify({"error": "File type not allowed"}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Route to serve the uploaded files securely."""
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

        # Generate a unique, short ID for the exhibit label
        label_id = str(uuid.uuid4())[:8]

        # Store the data in the SQLite database
        store_label_data(label_id, data)

        label_url = url_for('unified_exhibit_site', label_id=label_id)

        print(f"--- SUCCESS: Label {label_id} created. URL: {label_url} ---")
        return jsonify({
            "message": "Exhibit label data successfully saved.",
            "label_id": label_id,
            "url": label_url
        }), 201

    except Exception as e:
        print(f"ERROR during label creation: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500

# ----------------------------------------------------
# 4. Unified Site Structure (The New Viewer)
# ----------------------------------------------------
@app.route('/exhibit/<label_id>')
def unified_exhibit_site(label_id):
    """
    Renders the unified site base template, populating the sidebar 
    and loading the specified exhibit content.
    """
    # 1. Fetch all exhibit summaries for the sidebar
    all_exhibits = get_all_label_summaries()
    
    # 2. Fetch the specific exhibit data
    label_data = get_label_data(label_id)

    # 3. Handle 404 if the specific exhibit doesn't exist
    if not label_data:
        return render_template('error_404.html', label_id=label_id), 404

    # 4. Determine which content template to use based on the data
    template_type = label_data.get('template', 'minimalist')
    
    # Render the base template, which will automatically render the specific content template
    return render_template(
        'base_site.html',
        all_exhibits=all_exhibits,
        current_exhibit=label_data,
        current_template=f'{template_type}.html'
    )

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error_404.html', label_id='N/A'), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)