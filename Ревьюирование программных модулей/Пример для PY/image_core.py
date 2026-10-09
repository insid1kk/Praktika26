import logging
from pathlib import Path
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageEnhance

logger = logging.getLogger(__name__)

SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}


@dataclass
class ImageInfo:
    width: int
    height: int
    format: str
    file_size: int

    def __str__(self) -> str:
        return f"{self.width} x {self.height}, {self.format}, {self.file_size} B"


class ImageProcessor:
    """Библиотека обработки изображений (контракт для UI)."""

    def is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXT

    def load(self, path: str) -> Image.Image:
        if not Path(path).exists():
            raise FileNotFoundError(f"Файл не найден: {path}")
        if not self.is_supported(path):
            raise ValueError(f"Формат не поддерживается: {path}")

        logger.info("Загрузка изображения: %s", path)
        img = Image.open(path)
        return img.copy()  # отвязываем от файла

    def get_info(self, path: str) -> ImageInfo:
        if not Path(path).exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

        with Image.open(path) as img:
            info = ImageInfo(
                width=img.width,
                height=img.height,
                format=img.format or "UNKNOWN",
                file_size=Path(path).stat().st_size,
            )
        logger.info("Информация: %s", info)
        return info

    def to_grayscale(self, img: Image.Image) -> Image.Image:
        logger.info("Применение ч/б")
        return img.convert("L").convert("RGB")

    def blur(self, img: Image.Image, radius: int) -> Image.Image:
        if radius <= 0:
            return img.copy()
        logger.info("Размытие: radius=%s", radius)
        return img.filter(ImageFilter.GaussianBlur(radius=radius))

    def resize(self, img: Image.Image, width: int, height: int) -> Image.Image:
        if width <= 0 or height <= 0:
            raise ValueError("Ширина и высота должны быть > 0")
        logger.info("Resize: %sx%s", width, height)
        return img.resize((width, height), Image.LANCZOS)

    def apply_all(self, img: Image.Image, *,
                  grayscale: bool = False,
                  blur_radius: int = 0,
                  size: tuple[int, int] | None = None) -> Image.Image:
        """Применить все настройки последовательно."""
        result = img.copy()

        if grayscale:
            result = self.to_grayscale(result)

        if blur_radius > 0:
            result = self.blur(result, blur_radius)

        if size and size[0] > 0 and size[1] > 0:
            result = self.resize(result, size[0], size[1])

        return result

    def save(self, img: Image.Image, path: str) -> None:
        ext = Path(path).suffix.lower()
        if ext not in {".jpg", ".jpeg", ".png", ".bmp"}:
            raise ValueError(f"Формат сохранения не поддерживается: {ext}")

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        if ext in {".jpg", ".jpeg"}:
            img.convert("RGB").save(path, "JPEG", quality=95)
        else:
            img.save(path)

        logger.info("Сохранено: %s", path)