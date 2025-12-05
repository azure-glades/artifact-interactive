import uuid
import json
from flask import Flask, request, jsonify, render_template
from database import init_db, store_label_data, get_label_data

app = Flask(__name__)

# Initialize the database when the app starts
init_db(app)

# ----------------------------------------------------
# 1. Frontend Route (Serving the index.html content)
# ----------------------------------------------------
@app.route('/')
def home():
    # Placeholder: Assuming the user runs the HTML frontend separately, 
    return render_template('index.html')

# ----------------------------------------------------
# 2. API Route for Data Submission (Receiving JSON)
# ----------------------------------------------------
@app.route('/api/create_label', methods=['POST'])
def create_label():
    """
    Receives the JSON data from the frontend (Step 1), stores it, 
    and returns the unique URL for the digital label.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided in request body."}), 400

        # Generate a unique, short ID for the exhibit label
        label_id = str(uuid.uuid4())[:8] # Using first 8 chars of a UUID

        # Store the data in the SQLite database
        store_label_data(label_id, data)

        # Return the success message and the unique URL
        label_url = f"/label/{label_id}"

        print(f"--- SUCCESS: Label {label_id} created. URL: {label_url} ---")
        return jsonify({
            "message": "Exhibit label data successfully saved.",
            "label_id": label_id,
            "url": label_url
        }), 201

    except Exception as e:
        # Log the error for debugging purposes
        print(f"ERROR during label creation: {e}")
        return jsonify({"error": "Internal server error during data processing."}), 500

# ----------------------------------------------------
# 3. Route for Viewing the Final Label (Dynamic Rendering)
# ----------------------------------------------------
@app.route('/label/<label_id>')
def view_label(label_id):
    """
    Fetches the JSON data based on the label_id and renders the 
    corresponding Jinja template.
    """
    # 1. Fetch data from database
    label_data = get_label_data(label_id)

    if not label_data:
        return render_template('error_404.html', label_id=label_id), 404

    # 2. Determine template type
    template_type = label_data.get('template', 'minimalist')
    
    # Map the template key to the filename
    template_map = {
        'minimalist': 'minimalist.html',
        'timeline': 'timeline.html',
        'gallery': 'gallery.html',
    }
    
    template_file = template_map.get(template_type, 'minimalist_label.html')

    # 3. Render the specific template with the data
    # We pass the entire dictionary as a keyword argument 'data'
    return render_template(template_file, data=label_data)

# Optional: Add a simple 404 error template for completeness
@app.errorhandler(404)
def page_not_found(e):
    # If a route is not found, render a generic 404
    return render_template('error_404.html', label_id='N/A'), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)