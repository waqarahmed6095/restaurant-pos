import os

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


def load_preview_image(
    image_path: str,
    max_size: tuple[int, int],
    master,
):
    if Image is None or ImageTk is None or not image_path or not os.path.exists(image_path):
        return None
    try:
        image = Image.open(image_path)
        image.thumbnail(
            max_size,
            Image.Resampling.LANCZOS
            if hasattr(Image, "Resampling")
            else Image.ANTIALIAS,
        )
        return ImageTk.PhotoImage(image, master=master)
    except Exception:
        return None
