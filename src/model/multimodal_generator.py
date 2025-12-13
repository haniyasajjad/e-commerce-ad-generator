"""
Multi-modal Ad Creative Generator
Generates both text and visual layout for ads
"""

from PIL import Image, ImageDraw, ImageFont
import io
import base64
from dataclasses import dataclass
from typing import List, Tuple
import random

@dataclass
class AdLayout:
    """Ad layout configuration"""
    width: int = 1080  # Instagram post size
    height: int = 1080
    background_color: Tuple[int, int, int] = (255, 255, 255)
    primary_color: Tuple[int, int, int] = (255, 87, 51)  # Orange
    secondary_color: Tuple[int, int, int] = (33, 150, 243)  # Blue
    text_color: Tuple[int, int, int] = (33, 33, 33)  # Dark gray

class MultiModalAdGenerator:
    """Generates ad creatives with both text and visual layout"""
    
    # Pre-defined layout templates
    TEMPLATES = [
        "hero_centered",
        "split_vertical",
        "badge_corner",
        "gradient_overlay",
        "minimal_text"
    ]
    
    # Color schemes
    COLOR_SCHEMES = {
        "vibrant": {
            "bg": (255, 255, 255),
            "primary": (255, 87, 51),
            "secondary": (255, 193, 7),
            "text": (33, 33, 33)
        },
        "professional": {
            "bg": (245, 247, 250),
            "primary": (33, 150, 243),
            "secondary": (96, 125, 139),
            "text": (33, 33, 33)
        },
        "elegant": {
            "bg": (28, 28, 30),
            "primary": (255, 204, 0),
            "secondary": (172, 142, 104),
            "text": (255, 255, 255)
        },
        "fresh": {
            "bg": (255, 255, 255),
            "primary": (76, 175, 80),
            "secondary": (139, 195, 74),
            "text": (46, 125, 50)
        }
    }
    
    def __init__(self):
        # Try to load a nice font, fallback to default
        try:
            self.title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
            self.body_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)
            self.cta_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 50)
        except:
            # Fallback to default font
            self.title_font = ImageFont.load_default()
            self.body_font = ImageFont.load_default()
            self.cta_font = ImageFont.load_default()
    
    def generate_ad(self, 
                   title: str, 
                   body_text: str, 
                   cta: str = "Shop Now",
                   template: str = None,
                   color_scheme: str = "vibrant") -> dict:
        """
        Generate complete ad with text and layout
        
        Returns:
            dict with 'text', 'layout_type', 'image_base64'
        """
        # Select template and colors
        template = template or random.choice(self.TEMPLATES)
        colors = self.COLOR_SCHEMES.get(color_scheme, self.COLOR_SCHEMES["vibrant"])
        
        # Generate layout based on template
        if template == "hero_centered":
            image = self._create_hero_centered(title, body_text, cta, colors)
        elif template == "split_vertical":
            image = self._create_split_vertical(title, body_text, cta, colors)
        elif template == "badge_corner":
            image = self._create_badge_corner(title, body_text, cta, colors)
        elif template == "gradient_overlay":
            image = self._create_gradient_overlay(title, body_text, cta, colors)
        else:  # minimal_text
            image = self._create_minimal_text(title, body_text, cta, colors)
        
        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "text": body_text,
            "title": title,
            "cta": cta,
            "layout_type": template,
            "color_scheme": color_scheme,
            "image_base64": image_b64,
            "dimensions": {"width": 1080, "height": 1080}
        }
    
    def _create_hero_centered(self, title, body, cta, colors):
        """Hero image with centered text"""
        img = Image.new('RGB', (1080, 1080), colors["bg"])
        draw = ImageDraw.Draw(img)
        
        # Draw colored top section
        draw.rectangle([(0, 0), (1080, 400)], fill=colors["primary"])
        
        # Title (centered, white on colored bg)
        title_bbox = draw.textbbox((0, 0), title, font=self.title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text((540 - title_width/2, 150), title, fill=(255, 255, 255), font=self.title_font)
        
        # Body text (centered)
        body_lines = self._wrap_text(body, 30)
        y_offset = 500
        for line in body_lines[:3]:  # Max 3 lines
            bbox = draw.textbbox((0, 0), line, font=self.body_font)
            line_width = bbox[2] - bbox[0]
            draw.text((540 - line_width/2, y_offset), line, fill=colors["text"], font=self.body_font)
            y_offset += 60
        
        # CTA button
        self._draw_cta_button(draw, cta, (340, 850, 740, 950), colors)
        
        return img
    
    def _create_split_vertical(self, title, body, cta, colors):
        """Split layout with color block on left"""
        img = Image.new('RGB', (1080, 1080), colors["bg"])
        draw = ImageDraw.Draw(img)
        
        # Left color block
        draw.rectangle([(0, 0), (400, 1080)], fill=colors["primary"])
        
        # Vertical title on left
        draw.text((50, 400), title[:20], fill=(255, 255, 255), font=self.title_font)
        
        # Body on right
        body_lines = self._wrap_text(body, 25)
        y_offset = 200
        for line in body_lines[:5]:
            draw.text((450, y_offset), line, fill=colors["text"], font=self.body_font)
            y_offset += 60
        
        # CTA button
        self._draw_cta_button(draw, cta, (450, 850, 950, 950), colors)
        
        return img
    
    def _create_badge_corner(self, title, body, cta, colors):
        """Layout with promotional badge in corner"""
        img = Image.new('RGB', (1080, 1080), colors["bg"])
        draw = ImageDraw.Draw(img)
        
        # Top-right badge
        draw.ellipse([(800, 50), (1030, 280)], fill=colors["secondary"])
        draw.text((850, 130), "SALE", fill=(255, 255, 255), font=self.cta_font)
        
        # Title
        draw.text((80, 350), title[:25], fill=colors["text"], font=self.title_font)
        
        # Body
        body_lines = self._wrap_text(body, 35)
        y_offset = 500
        for line in body_lines[:4]:
            draw.text((80, y_offset), line, fill=colors["text"], font=self.body_font)
            y_offset += 60
        
        # CTA
        self._draw_cta_button(draw, cta, (80, 850, 580, 950), colors)
        
        return img
    
    def _create_gradient_overlay(self, title, body, cta, colors):
        """Gradient background effect"""
        img = Image.new('RGB', (1080, 1080), colors["bg"])
        draw = ImageDraw.Draw(img)
        
        # Simple gradient effect (top to bottom)
        for y in range(1080):
            alpha = y / 1080
            color = self._interpolate_color(colors["primary"], colors["secondary"], alpha)
            draw.line([(0, y), (1080, y)], fill=color, width=1)
        
        # Title (white for contrast)
        draw.text((100, 200), title[:25], fill=(255, 255, 255), font=self.title_font)
        
        # Body (white)
        body_lines = self._wrap_text(body, 30)
        y_offset = 450
        for line in body_lines[:4]:
            draw.text((100, y_offset), line, fill=(255, 255, 255), font=self.body_font)
            y_offset += 60
        
        # CTA
        self._draw_cta_button(draw, cta, (100, 850, 600, 950), colors, fill=(255, 255, 255))
        
        return img
    
    def _create_minimal_text(self, title, body, cta, colors):
        """Minimalist text-only design"""
        img = Image.new('RGB', (1080, 1080), colors["bg"])
        draw = ImageDraw.Draw(img)
        
        # Thin accent line
        draw.rectangle([(100, 300), (980, 310)], fill=colors["primary"])
        
        # Title
        draw.text((100, 400), title[:30], fill=colors["text"], font=self.title_font)
        
        # Body
        body_lines = self._wrap_text(body, 40)
        y_offset = 550
        for line in body_lines[:5]:
            draw.text((100, y_offset), line, fill=colors["text"], font=self.body_font)
            y_offset += 55
        
        # Simple text CTA
        draw.text((100, 900), cta, fill=colors["primary"], font=self.cta_font)
        
        return img
    
    def _draw_cta_button(self, draw, text, coords, colors, fill=None):
        """Draw a call-to-action button"""
        x1, y1, x2, y2 = coords
        button_color = fill if fill else colors["primary"]
        
        # Button background
        draw.rectangle(coords, fill=button_color, outline=colors["secondary"], width=3)
        
        # Button text (centered)
        bbox = draw.textbbox((0, 0), text, font=self.cta_font)
        text_width = bbox[2] - bbox[0]
        text_x = (x1 + x2) / 2 - text_width / 2
        text_y = (y1 + y2) / 2 - 25
        
        text_color = colors["text"] if fill == (255, 255, 255) else (255, 255, 255)
        draw.text((text_x, text_y), text, fill=text_color, font=self.cta_font)
    
    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        """Wrap text into lines"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    def _interpolate_color(self, color1, color2, alpha):
        """Interpolate between two colors"""
        return tuple(int(c1 * (1 - alpha) + c2 * alpha) for c1, c2 in zip(color1, color2))

# Global instance
multimodal_generator = MultiModalAdGenerator()