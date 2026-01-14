from PIL import Image, ImageDraw

# Create a 100x100 white image
img = Image.new('RGB', (100, 100), color='white')
draw = ImageDraw.Draw(img)

# Draw some obstacles (black rectangles)
draw.rectangle([30, 0, 70, 70], fill='black')
draw.rectangle([10, 80, 90, 90], fill='black')

img.save('example_map.png')
print("Created example_map.png")
