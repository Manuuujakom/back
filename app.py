from flask import Flask, request, jsonify
from flask_cors import CORS
from rembg import remove
from PIL import Image
import base64
import io

app = Flask(__name__)
CORS(app) # Enable CORS for all origins (for development)

def decode_image(base64_string):
    """Decodes a Base64 string to a PIL Image."""
    try:
        image_bytes = base64.b64decode(base64_string)
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        app.logger.error(f"Error decoding image: {e}")
        return None

def encode_image(image):
    """Encodes a PIL Image to a Base64 string with PNG prefix."""
    try:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        app.logger.error(f"Error encoding image: {e}")
        return None

@app.route('/api/remove-background', methods=['POST'])
def remove_background():
    """Removes the background from an uploaded image."""
    if 'image_data' not in request.form:
        return jsonify({"error": "No image_data provided"}), 400

    image_data_b64 = request.form['image_data']
    input_image = decode_image(image_data_b64)

    if input_image is None:
        return jsonify({"error": "Invalid image data"}), 400

    try:
        # Using rembg to remove the background
        output_image = remove(input_image)
        processed_image_b64 = encode_image(output_image)

        if processed_image_b64 is None:
            return jsonify({"error": "Failed to encode processed image"}), 500

        return jsonify({
            "image_data": processed_image_b64,
            "message": "Background removed successfully!"
        }), 200
    except Exception as e:
        app.logger.error(f"Error during background removal: {e}")
        return jsonify({"error": "Failed to remove background", "details": str(e)}), 500

@app.route('/api/edit-background', methods=['POST'])
def edit_background():
    """Applies either a solid color or another image as the background to the current processed image."""
    if 'image_data' not in request.form:
        return jsonify({"error": "No image_data provided"}), 400

    image_data_b64 = request.form['image_data']
    current_image = decode_image(image_data_b64)

    if current_image is None:
        return jsonify({"error": "Invalid current image data"}), 400

    color = request.form.get('color')
    background_image_file = request.files.get('background_image')

    if not color and not background_image_file:
        return jsonify({"error": "Either 'color' or 'background_image' must be provided"}), 400

    try:
        # Create a new blank image for the background
        new_background = Image.new("RGBA", current_image.size)

        if background_image_file:
            # Use provided image as background
            bg_image = Image.open(io.BytesIO(background_image_file.read())).convert("RGBA")
            # Resize background image to match current_image dimensions
            bg_image = bg_image.resize(current_image.size, Image.Resampling.LANCZOS)
            new_background.paste(bg_image, (0, 0))
        elif color:
            # Use solid color as background
            # Convert hex to RGB tuple
            hex_color = color.lstrip('#')
            try:
                rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4)) + (255,) # Add alpha for RGBA
            except ValueError:
                return jsonify({"error": "Invalid color hex code"}), 400
            new_background = Image.new("RGBA", current_image.size, rgb_color)

        # Composite the current image over the new background
        # Use the alpha channel of the current_image for transparency
        final_image = Image.alpha_composite(new_background, current_image)
        processed_image_b64 = encode_image(final_image)

        if processed_image_b64 is None:
            return jsonify({"error": "Failed to encode processed image"}), 500

        return jsonify({
            "image_data": processed_image_b64,
            "message": "Background edited successfully!"
        }), 200
    except Exception as e:
        app.logger.error(f"Error during background editing: {e}")
        return jsonify({"error": "Failed to edit background", "details": str(e)}), 500

@app.route('/api/resize-image', methods=['POST'])
def resize_image():
    """Resizes the current processed image to specified dimensions."""
    if 'image_data' not in request.form:
        return jsonify({"error": "No image_data provided"}), 400

    image_data_b64 = request.form['image_data']
    current_image = decode_image(image_data_b64)

    if current_image is None:
        return jsonify({"error": "Invalid current image data"}), 400

    width_str = request.form.get('width')
    height_str = request.form.get('height')

    width = None
    height = None

    if width_str:
        try:
            width = int(width_str)
            if width <= 0:
                return jsonify({"error": "Width must be a positive integer"}), 400
        except ValueError:
            return jsonify({"error": "Invalid width parameter"}), 400

    if height_str:
        try:
            height = int(height_str)
            if height <= 0:
                return jsonify({"error": "Height must be a positive integer"}), 400
        except ValueError:
            return jsonify({"error": "Invalid height parameter"}), 400

    if width is None and height is None:
        # If neither width nor height is provided, return the image as is
        processed_image_b64 = encode_image(current_image)
        if processed_image_b64 is None:
            return jsonify({"error": "Failed to encode image"}), 500
        return jsonify({
            "image_data": processed_image_b64,
            "message": "No dimensions provided, image returned as is."
        }), 200

    try:
        original_width, original_height = current_image.size

        if width and height:
            # Resize to exact dimensions
            resized_image = current_image.resize((width, height), Image.Resampling.LANCZOS)
        elif width:
            # Resize proportionally based on width
            aspect_ratio = original_height / original_width
            new_height = int(width * aspect_ratio)
            resized_image = current_image.resize((width, new_height), Image.Resampling.LANCZOS)
        elif height:
            # Resize proportionally based on height
            aspect_ratio = original_width / original_height
            new_width = int(height * aspect_ratio)
            resized_image = current_image.resize((new_width, height), Image.Resampling.LANCZOS)
        
        processed_image_b64 = encode_image(resized_image)

        if processed_image_b64 is None:
            return jsonify({"error": "Failed to encode processed image"}), 500

        return jsonify({
            "image_data": processed_image_b64,
            "message": "Image resized successfully!"
        }), 200
    except Exception as e:
        app.logger.error(f"Error during image resizing: {e}")
        return jsonify({"error": "Failed to resize image", "details": str(e)}), 500

@app.route('/')
def home():
    return "Image Processing Backend is running!"

if __name__ == '__main__':
    # Use Gunicorn in production, this is for local development
    app.run(host='0.0.0.0', port=5000, debug=True)