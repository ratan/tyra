# create_template.py
# A simple script to generate the background image for Tyra's shareable insights.
# Requires Pillow: pip install Pillow

from PIL import Image
import os

# --- Configuration ---
WIDTH, HEIGHT = 1000, 1000
# A nice thematic gradient from the app's purple to a soft pink
START_COLOR = (139, 74, 156)  # RGB for --primary-color
END_COLOR = (236, 88, 142)    # RGB for a complementary pink/fuchsia
IMAGE_NAME = "insight_template.png"
OUTPUT_DIR = os.path.join("../static", "images")

def generate_gradient_image():
    """Creates a 1000x1000px vertical gradient image and saves it."""
    
    print(f"Ensuring directory '{OUTPUT_DIR}' exists...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Creating a new {WIDTH}x{HEIGHT} image canvas...")
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = img.load()

    print("Generating purple-to-pink gradient...")
    for y in range(HEIGHT):
        # Calculate the ratio for this row (0.0 at top, 1.0 at bottom)
        ratio = y / (HEIGHT - 1)
        
        # Interpolate each color channel
        r = int(START_COLOR[0] * (1 - ratio) + END_COLOR[0] * ratio)
        g = int(START_COLOR[1] * (1 - ratio) + END_COLOR[1] * ratio)
        b = int(START_COLOR[2] * (1 - ratio) + END_COLOR[2] * ratio)
        
        # Draw a horizontal line of this color
        for x in range(WIDTH):
            draw[x, y] = (r, g, b)

    output_path = os.path.join(OUTPUT_DIR, IMAGE_NAME)
    print(f"Saving image to '{output_path}'...")
    img.save(output_path, "PNG")
    print("\n✅ Success! Your 'insight_template.png' has been created.")

if __name__ == "__main__":
    generate_gradient_image()