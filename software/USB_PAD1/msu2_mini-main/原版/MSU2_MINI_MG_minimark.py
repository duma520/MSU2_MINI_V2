from PIL import Image, ImageDraw, ImageFont

# Font cache
font_cache = {}
# Image cache
image_cache = {}

def load_font(font_name, font_size):
    key = (font_name, font_size)
    if key not in font_cache:
        try:
            font_cache[key] = ImageFont.truetype(font_name, font_size)
        except (OSError, ValueError):
            print(f"Warning: font {key} load failed")
            font_cache[key] = ImageFont.load_default(font_size)
    return font_cache[key]

def load_image(image_path):
    if image_path not in image_cache:
        try:
            image_cache[image_path] = Image.open(image_path).convert('RGBA')  # Convert to RGBA
        except FileNotFoundError:
            print(f"Warning: image {image_path} load failed")
            image_cache[image_path] = Image.new('RGBA', (16, 16), (255, 0, 255)) # 没有图片，弄一个品红色的图片代替
    return image_cache[image_path]

class MiniMarkParser:
    def __init__(self):
        self.reset_state()
        
    def reset_state(self):
        self.position = (0, 0)  # Current drawing position
        self.font = load_font("arial.ttf", 20)  # Default font
        self.color = (0, 0, 0)  # Default color (black)
        self.anchor = "la"

    def parse_line(self, line, draw, img, record_dict=None, record_dict_value=None):
        parts = line.split()
        command = parts[0]

        if command == 'a':
            # Change text anchor point (not directly implemented)
            self.anchor = parts[1]

        elif command == 'p':
            text = ' '.join(parts[1:])
            draw.text(self.position, text, fill=self.color, font=self.font, anchor=self.anchor)
            # Calculate the width of the drawn text
            text_width = round(draw.textlength(text, font=self.font))

            # Advance position if anchor contains "l"
            if "l" in self.anchor:
                self.position = (self.position[0] + text_width, self.position[1])
            # Advance position if anchor contains "r"
            if "r" in self.anchor:
                self.position = (self.position[0] - text_width, self.position[1])

        elif command == 'm':
            x, y = map(int, parts[1:3])
            self.position = (x, y)

        elif command == 't':
            dx, dy = map(int, parts[1:3])
            self.position = (self.position[0] + dx, self.position[1] + dy)

        elif command == 'f':
            font_name = parts[1]
            font_size = int(parts[2])
            self.font = load_font(font_name, font_size)

        elif command == 'c':
            hex_color = parts[1]
            hex_color = hex_color.lstrip('#')
            self.color = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))  # Convert hex to RGB

        elif command == 'i':
            image_path = parts[1]
            image = load_image(image_path)
            # Paste the image onto the main image at the current position
            img.paste(image, self.position, image)  # Use image as mask for transparency
        elif command == 'v' and record_dict is not None:
            if len(parts) <= 2 or record_dict_value is None:
                key = parts[1]
                text = record_dict.get(key, f"<{key}>")
            else:
                key = parts[1]
                formatting = parts[2]
                value = record_dict_value.get(key)
                if value is not None:
                    text = formatting.format(value)
                else:
                    text = f'<{key}>'
            draw.text(self.position, text, fill=self.color, font=self.font, anchor=self.anchor)
            # Calculate the width of the drawn text
            text_width = round(draw.textlength(text, font=self.font))

            # Advance position if anchor contains "l"
            if "l" in self.anchor:
                self.position = (self.position[0] + text_width, self.position[1])
            # Advance position if anchor contains "r"
            if "r" in self.anchor:
                self.position = (self.position[0] - text_width, self.position[1])

    def parse(self, size, lines, record_dict=None, record_dict_value=None):
        # Create a new image and draw context
        img = Image.new('RGBA', size, color=(255, 255, 255, 0))  # Use RGBA to support transparency
        draw = ImageDraw.Draw(img)

        for line in lines:
            self.parse_line(line, draw, img, record_dict, record_dict_value)

        return img

# Example usage
if __name__ == "__main__":
    parser = MiniMarkParser()

    # Sample dictionary for the 'v' command
    sample_dict = {
        "name": "Alice",
        "age": "30",
        "city": "Wonderland"
    }

    commands = [
        "m 100 100",          # Move to (100, 100)
        "i test.png",         # Draw an image (ensure the path is correct)
        "m 100 100",          # Move to (100, 100)
        "f arial.ttf 24",     # Set font to Arial size 24
        "c #FF5733",          # Set color to a hex value
        "p Hello World!",      # Draw text
        "t 0 40",             # Move down
        "p This is a test.",   # Draw more text
        "m 0 0",             # Move down
        "v name",             # Lookup 'name' in dictionary
        "v age",              # Lookup 'age' in dictionary
        "v city",             # Lookup 'city' in dictionary
        "v non_existing_key"  # Test with a non-existing key
    ]
    # Parse commands and create the image
    image = parser.parse((400, 400), commands, record_dict=sample_dict)
    image.show()  # Display the image (you can also save it using image.save('output.png'))