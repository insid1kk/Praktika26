from PIL import Image, ImageFilter

class ImageProcessor:
    def load(self, path):
        return Image.open(path)

    def process(self, img, gray, blur, w, h):
        res = img.convert('L').convert('RGB') if gray else img.copy()
        if blur > 0: res = res.filter(ImageFilter.GaussianBlur(blur))
        return res.resize((w, h)) if (w, h) != img.size else res

    def save(self, img, path):
        img.save(path)