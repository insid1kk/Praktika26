import logging
import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from image_ui import MainWindow, LOGS_DIR, CONFIGS_DIR, OUTPUT_DIR


def setup_folders() -> None:
    for folder in (LOGS_DIR, CONFIGS_DIR, OUTPUT_DIR):
        Path(folder).mkdir(parents=True, exist_ok=True)


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    setup_folders()
    setup_logging()

    app = QApplication(sys.argv)

    # глобальный перехват ошибок
    def excepthook(exc_type, exc_value, exc_tb):
        logging.getLogger(__name__).exception(
            "Необработанное исключение", exc_info=(exc_type, exc_value, exc_tb)
        )
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Ошибка", str(exc_value))

    sys.excepthook = excepthook

    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())