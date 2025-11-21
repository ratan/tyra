import os
from PIL import Image, ImageDraw

# Ensure directory exists
ASSETS_DIR = os.path.join('../static', 'images')
os.makedirs(ASSETS_DIR, exist_ok=True)

def create_icon(filename, bg_color, symbol_color, symbol_type):
    size = (128, 128)
    img = Image.new('RGBA', size, (0, 0, 0, 0)) # Transparent background
    draw = ImageDraw.Draw(img)

    # Draw Base Circle/Squircle
    draw.rounded_rectangle([(0, 0), size], radius=30, fill=bg_color)

    # Draw Symbol
    if symbol_type == 'notes':
        # Draw lines representing text
        draw.rectangle([(30, 30), (98, 40)], fill=symbol_color)
        draw.rectangle([(30, 55), (98, 65)], fill=symbol_color)
        draw.rectangle([(30, 80), (70, 90)], fill=symbol_color)
    
    elif symbol_type == 'weather':
        # Draw Sun (Yellow circle) and Cloud (White rect overlap)
        draw.ellipse([(20, 20), (90, 90)], fill='#f39c12') # Sun
        draw.rounded_rectangle([(40, 70), (110, 100)], radius=15, fill='#ecf0f1') # Cloud
    
    elif symbol_type == 'calendar':
        # Draw Red Header
        draw.rounded_rectangle([(0, 0), (127, 40)], radius=30, fill='#e74c3c', corners=(True, True, False, False))
        # Draw date lines
        draw.rectangle([(30, 60), (98, 100)], fill='#bdc3c7') 

    elif symbol_type == 'journal':
        # Draw darker binding on the left
        draw.rectangle([(0, 0), (30, 128)], fill='#145a32') # Dark binding
        # Draw label on cover
        draw.rectangle([(40, 30), (110, 60)], fill='#145a32')

    filepath = os.path.join(ASSETS_DIR, filename)
    img.save(filepath)
    print(f"Generated: {filepath}")

if __name__ == "__main__":
    print("Generating Discreet Mode Icons...")
    
    # 1. Notes Icon (Yellow)
    create_icon("icon_notes.png", "#f1c40f", "#ffffff", "notes")
    
    # 2. Weather Icon (Sky Blue)
    create_icon("icon_weather.png", "#3498db", "#f39c12", "weather")
    
    # 3. Calendar Icon (White)
    create_icon("icon_calendar.png", "#ecf0f1", "#e74c3c", "calendar")

    # 4. Journal Icon (Green Notebook)
    create_icon("icon_journal.png", "#27ae60", "#145a32", "journal")
    
    print("Done! Refresh your dashboard.")