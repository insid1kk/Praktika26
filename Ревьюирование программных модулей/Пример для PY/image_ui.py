import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QFileDialog, QSlider, QCheckBox, QSpinBox, QMessageBox,
    QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout,
)

from image_core import ImageProcessor, ImageInfo

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
CONFIGS_DIR = BASE_DIR / "configs"
OUTPUT_DIR = BASE_DIR / "output"


# ─────────────────────────────────────────────────────
# Вспомогательные сервисы (настройки и история)
# ─────────────────────────────────────────────────────
class SettingsService:
    def __init__(self) -> None:
        self.path = CONFIGS_DIR / "settings.json"
        self.data = self._load()

    def _load(self) -> dict:
        try:
            if self.path.exists():
                return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Не удалось загрузить настройки: %s", e)
        return {"last_open_dir": "", "last_save_dir": ""}

    def save(self) -> None:
        try:
            self.path.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Не удалось сохранить настройки: %s", e)


class HistoryService:
    def __init__(self) -> None:
        self.path = OUTPUT_DIR / "history.json"
        self.entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                self.entries = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Не удалось загрузить историю: %s", e)

    def add(self, operation: str, **params) -> None:
        self.entries.append({
            "date": datetime.now().isoformat(timespec="seconds"),
            "operation": operation,
            "params": params,
        })
        try:
            self.path.write_text(
                json.dumps(self.entries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Не удалось сохранить историю: %s", e)


# ─────────────────────────────────────────────────────
# Окно
# ─────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Обработка изображений")
        self.resize(1000, 650)
        self.setAcceptDrops(True)

        # Логика
        self.processor = ImageProcessor()
        self.settings = SettingsService()
        self.history = HistoryService()

        # Состояние
        self.original_img = None       # PIL.Image — исходное
        self.processed_img = None      # PIL.Image — результат
        self.previous_img = None       # для undo
        self.current_path: str | None = None

        self._build_ui()

    # ───── UI ─────
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)

        # Левая панель управления
        left = QVBoxLayout()

        btn_load = QPushButton("Загрузить изображение")
        btn_load.clicked.connect(self.on_load)
        left.addWidget(btn_load)

        # Группа "Ч/б"
        self.chk_gray = QCheckBox("Чёрно-белый")
        left.addWidget(self.chk_gray)

        # Группа "Размытие"
        blur_box = QGroupBox("Размытие (радиус)")
        blur_layout = QVBoxLayout(blur_box)
        self.sld_blur = QSlider(Qt.Horizontal)
        self.sld_blur.setRange(0, 10)
        self.sld_blur.valueChanged.connect(
            lambda v: self.lbl_blur.setText(str(v))
        )
        self.lbl_blur = QLabel("0")
        self.lbl_blur.setAlignment(Qt.AlignCenter)
        blur_layout.addWidget(self.sld_blur)
        blur_layout.addWidget(self.lbl_blur)
        left.addWidget(blur_box)

        # Группа "Размер"
        size_box = QGroupBox("Размер")
        form = QFormLayout(size_box)
        self.spn_w = QSpinBox()
        self.spn_w.setRange(1, 10000)
        self.spn_h = QSpinBox()
        self.spn_h.setRange(1, 10000)
        form.addRow("Ширина:", self.spn_w)
        form.addRow("Высота:", self.spn_h)
        left.addWidget(size_box)

        # Кнопки действий
        btn_apply = QPushButton("Применить")
        btn_apply.clicked.connect(self.on_apply)
        left.addWidget(btn_apply)

        btn_undo = QPushButton("Отменить")
        btn_undo.clicked.connect(self.on_undo)
        left.addWidget(btn_undo)

        btn_save = QPushButton("Сохранить...")
        btn_save.clicked.connect(self.on_save)
        left.addWidget(btn_save)

        # Блок информации
        self.lbl_info = QLabel("Информация не загружена")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setStyleSheet("color: #555; font-style: italic;")
        left.addWidget(self.lbl_info)
        left.addStretch()

        root.addLayout(left, 1)

        # Правая часть — два изображения
        self.lbl_original = self._make_image_label("Исходное изображение")
        self.lbl_processed = self._make_image_label("Результат")

        right = QHBoxLayout()
        right.addWidget(self.lbl_original, 1)
        right.addWidget(self.lbl_processed, 1)
        root.addLayout(right, 3)

    @staticmethod
    def _make_image_label(title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setMinimumSize(280, 280)
        lbl.setStyleSheet(
            "QLabel { border: 1px solid #888; background: #f4f4f4; }"
        )
        return lbl

    # ───── Drag & Drop ─────
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.load_from_path(path)
                break

    # ───── Загрузка ─────
    def on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть изображение",
            self.settings.data.get("last_open_dir", ""),
            "Изображения (*.jpg *.jpeg *.png *.bmp *.gif *.tiff)",
        )
        if path:
            self.load_from_path(path)

    def load_from_path(self, path: str) -> None:
        try:
            img = self.processor.load(path)
            info = self.processor.get_info(path)
        except Exception as e:
            logger.exception("Ошибка загрузки")
            QMessageBox.critical(self, "Ошибка", str(e))
            return

        self.original_img = img
        self.processed_img = img.copy()
        self.previous_img = None
        self.current_path = path

        # обновляем поля размера
        self.spn_w.setValue(img.width)
        self.spn_h.setValue(img.height)

        self.lbl_info.setText(
            f"Ширина: {info.width}\n"
            f"Высота: {info.height}\n"
            f"Формат: {info.format}\n"
            f"Размер: {info.file_size} байт"
        )

        self._refresh_images()

        self.settings.data["last_open_dir"] = str(Path(path).parent)
        self.settings.save()
        self.history.add("load", path=path)

    # ───── Обработка ─────
    def on_apply(self) -> None:
        if self.original_img is None:
            QMessageBox.information(self, "Нет изображения",
                                    "Сначала загрузите изображение")
            return

        try:
            # undo
            self.previous_img = self.processed_img.copy() \
                if self.processed_img else None

            size = (self.spn_w.value(), self.spn_h.value())
            self.processed_img = self.processor.apply_all(
                self.original_img,
                grayscale=self.chk_gray.isChecked(),
                blur_radius=self.sld_blur.value(),
                size=size,
            )

            self._refresh_images()
            self.history.add(
                "apply",
                grayscale=self.chk_gray.isChecked(),
                blur_radius=self.sld_blur.value(),
                width=size[0],
                height=size[1],
            )
        except Exception as e:
            logger.exception("Ошибка обработки")
            QMessageBox.critical(self, "Ошибка обработки", str(e))

    def on_undo(self) -> None:
        if self.previous_img is None:
            QMessageBox.information(self, "Отмена",
                                    "Нечего отменять")
            return
        self.processed_img = self.previous_img
        self.previous_img = None
        self._refresh_images()
        self.history.add("undo")

    # ───── Сохранение ─────
    def on_save(self) -> None:
        if self.processed_img is None:
            QMessageBox.information(self, "Нет результата",
                                    "Сначала обработайте изображение")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить как",
            self.settings.data.get("last_save_dir", ""),
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)",
        )
        if not path:
            return

        try:
            self.processor.save(self.processed_img, path)
            self.settings.data["last_save_dir"] = str(Path(path).parent)
            self.settings.save()
            self.history.add("save", path=path)
            QMessageBox.information(self, "Готово", "Файл сохранён")
        except Exception as e:
            logger.exception("Ошибка сохранения")
            QMessageBox.critical(self, "Ошибка сохранения", str(e))

    # ───── Утилита: показать изображения ─────
    def _refresh_images(self) -> None:
        if self.original_img is not None:
            self._set_pixmap(self.lbl_original, self.original_img)
        if self.processed_img is not None:
            self._set_pixmap(self.lbl_processed, self.processed_img)

    @staticmethod
    def _set_pixmap(label: QLabel, img) -> None:
        """PIL.Image → QPixmap с сохранением пропорций."""
        if img.mode != "RGB":
            img = img.convert("RGB")

        data = img.tobytes("raw", "RGB")
        qimg = QImage(data, img.width, img.height,
                      img.width * 3, QImage.Format_RGB888)

        pix = QPixmap.fromImage(qimg)
        label.setPixmap(pix.scaled(
            label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_images()