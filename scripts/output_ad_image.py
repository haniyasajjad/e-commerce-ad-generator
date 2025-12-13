import json
import base64

# Change this to the path of your JSON file
json_file_path = '/Users/mac/Downloads/response_1765615929314.json'  # e.g., 'ad_response.json'

# Output image file
output_image_path = 'output_ad_image.png'

with open(json_file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extract the base64 string
image_base64 = data['layout']['image_base64']

# Decode and save the image
image_data = base64.b64decode(image_base64)

with open(output_image_path, 'wb') as img_file:
    img_file.write(image_data)

print(f"Image successfully saved to {output_image_path}")
print(f"Dimensions: {data['layout']['dimensions']['width']}x{data['layout']['dimensions']['height']}")