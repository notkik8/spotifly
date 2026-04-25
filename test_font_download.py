import os, urllib.request

url = "https://raw.githubusercontent.com/cygnus-rom/external_inter-fonts/caf-ten/Inter-Bold.ttf"
urllib.request.urlretrieve(url, "test_inter.ttf")
from PIL import ImageFont
font = ImageFont.truetype("test_inter.ttf", 24)
print("Font loaded successfully:", font.getname())
print("Cyrillic test bbox:", font.getmask("Привет").getbbox())
