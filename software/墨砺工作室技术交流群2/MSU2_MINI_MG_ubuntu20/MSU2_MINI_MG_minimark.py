#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys

from PIL import Image, ImageDraw, ImageFont

# Font cache
font_cache = {}
# Image cache
image_cache = {}


# 优先尝试启动路径，也就是资源文件可以在启动路径修改
def get_resource(relative_path):
    base_path = os.path.dirname(os.path.realpath(sys.argv[0]))  # 启动路径
    path = os.path.normpath(os.path.join(base_path, relative_path))
    if os.path.isfile(path):
        return path
    base_path = getattr(sys, "_MEIPASS", None)  # pyinstaller打包后的路径
    if base_path is None:
        base_path = os.path.dirname(__file__)  # py文件路径
    return os.path.normpath(os.path.join(base_path, relative_path))


def load_font(font_name, font_size):
    key = (font_name, font_size)
    if key not in font_cache:
        try:
            font_cache[key] = ImageFont.truetype(get_resource(font_name), font_size)
        except (OSError, ValueError) as e:
            try:
                font_cache[key] = ImageFont.truetype(get_resource("./simhei.ttf"), font_size)
            except (OSError, ValueError) as e:
                print("Warning: font %s load failed, %s:%s" % (key, type(e), e))
                font_cache[key] = ImageFont.load_default(font_size)
    return font_cache[key]


def load_image(image_path):
    if image_path not in image_cache:
        image = None
        try:
            image = Image.open(get_resource(image_path))
            # Convert to RGBA
            image_cache[image_path] = image.convert("RGBA")
        except FileNotFoundError as e:
            print("Warning: image %s load failed: %s" % (image_path, e))
            # 没有图片，弄一个品红色的图片代替
            image_default = "default"
            if image_default not in image_cache:
                image_cache[image_default] = Image.new("RGBA", (16, 16), (255, 0, 255))
            return image_cache[image_default]
        finally:
            if image is not None:
                image.close()
    return image_cache[image_path]


class MiniMarkParser:
    def __init__(self):
        self.anchor = None
        self.color = None
        self.font = None
        self.position = None
        self.reset_state()

    def reset_state(self):
        self.position = (0, 0)  # Current drawing position
        self.font = load_font("./simhei.ttf", 20)  # Default font
        self.color = (0, 0, 0)  # Default color (black)
        self.anchor = "la"

    def parse_line(self, line, draw, img, record_dict=None):
        parts = line.split()
        if len(parts) == 0:
            return
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
            if len(parts) > 3:
                font_name = line[line.index(parts[0]) + 1:line.rindex(parts[-1])].strip()
                font_size = int(parts[-1])
            else:
                font_name = parts[1]
                font_size = int(parts[2])
            self.font = load_font(font_name, font_size)

        elif command == 'c':
            hex_color = parts[1]
            hex_color = hex_color.lstrip('#')
            # Convert hex to RGB
            self.color = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        elif command == 'i':
            if len(parts) > 2:
                image_path = line[line.index(parts[0]) + 1:].strip()
            else:
                image_path = parts[1]
            image = load_image(image_path)
            # Paste the image onto the main image at the current position
            img.paste(image, self.position, image)  # Use image as mask for transparency

        elif command == 'v' and record_dict is not None:
            key = parts[1]
            pairs = record_dict.get(key, None)
            if pairs is None:
                text = "<%s>" % key
            elif len(parts) <= 2:
                text = pairs[0]
            elif pairs[1] is None:
                text = "<%s>" % key
            else:
                formatting = parts[2]
                text = formatting.format(pairs[1])
            draw.text(self.position, text, fill=self.color, font=self.font, anchor=self.anchor)
            # Calculate the width of the drawn text
            text_width = round(draw.textlength(text, font=self.font))

            # Advance position if anchor contains "l"
            if "l" in self.anchor:
                self.position = (self.position[0] + text_width, self.position[1])
            # Advance position if anchor contains "r"
            if "r" in self.anchor:
                self.position = (self.position[0] - text_width, self.position[1])

    def parse(self, size, lines, record_dict=None):
        # Create a new image and draw context
        # Use RGBA to support transparency
        img = Image.new("RGBA", size, color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        for line in lines:
            self.parse_line(line, draw, img, record_dict)

        return img


# Example usage
if __name__ == "__main__":
    parser = MiniMarkParser()

    # Sample dictionary for the 'v' command
    sample_dict = {
        "name": ("Alice"),
        "age": ("30"),
        "city": ("Wonderland")
    }

    commands = [
        "m 100 100",  # Move to (100, 100)
        "i test.png",  # Draw an image (ensure the path is correct)
        "m 100 100",  # Move to (100, 100)
        "f ./arial.ttf 24",  # Set font to Arial size 24
        "c #FF5733",  # Set color to a hex value
        "p Hello World!",  # Draw text
        "t 0 40",  # Move down
        "p This is a test.",  # Draw more text
        "m 0 0",  # Move down
        "v name",  # Lookup "name" in dictionary
        "v age",  # Lookup "age" in dictionary
        "v city",  # Lookup "city" in dictionary
        "v non_existing_key"  # Test with a non-existing key
    ]
    # Parse commands and create the image
    image = parser.parse((400, 400), commands, record_dict=sample_dict)
    # Display the image (you can also save it using image.save("output.png"))
    image.show()
