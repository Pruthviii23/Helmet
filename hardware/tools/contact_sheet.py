import sys, glob, os
from PIL import Image, ImageDraw
pat, out = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
fs = sorted(glob.glob(pat))
W, H = Image.open(fs[0]).size
rows = (len(fs) + cols - 1) // cols
sheet = Image.new("RGB", (W * cols, H * rows), (14, 16, 20))
d = ImageDraw.Draw(sheet)
for i, f in enumerate(fs):
    im = Image.open(f).convert("RGBA")
    bg = Image.new("RGBA", im.size, (14, 16, 20, 255)); bg.alpha_composite(im)
    x, y = (i % cols) * W, (i // cols) * H
    sheet.paste(bg.convert("RGB"), (x, y))
    d.text((x + 12, y + 10), os.path.basename(f), fill=(200, 200, 200))
sheet.save(out, quality=88)
