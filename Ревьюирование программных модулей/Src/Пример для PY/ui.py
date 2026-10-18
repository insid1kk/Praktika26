import os
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from core import ImageProcessor

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.p = ImageProcessor()
        self.img = self.res = self.prev = None
        self.setWindowTitle("Обработка изображений")
        self.resize(1000, 600)
        self.setAcceptDrops(True)

        main = QWidget()
        self.setCentralWidget(main)
        lay = QHBoxLayout(main)

        # Левая панель
        left = QVBoxLayout()
        btn_load = QPushButton("Загрузить"); btn_load.clicked.connect(self.load)
        self.chk = QCheckBox("Ч/б")
        self.sld = QSlider(Qt.Horizontal); self.sld.setRange(0, 10)
        self.sp_w = QSpinBox(); self.sp_h = QSpinBox()
        for sp in (self.sp_w, self.sp_h): sp.setRange(1, 5000)
        btn_apply = QPushButton("Применить"); btn_apply.clicked.connect(self.apply)
        btn_undo = QPushButton("Отменить"); btn_undo.clicked.connect(self.undo)
        btn_save = QPushButton("Сохранить"); btn_save.clicked.connect(self.save)
        self.lbl_info = QLabel("Информация:")

        for w in (btn_load, self.chk, QLabel("Размытие:"), self.sld,
                  QLabel("Ширина:"), self.sp_w, QLabel("Высота:"), self.sp_h,
                  btn_apply, btn_undo, btn_save, self.lbl_info):
            left.addWidget(w)
        left.addStretch()
        lay.addLayout(left, 1)

        # Правая панель (картинки)
        self.lbl_orig = QLabel("Исходное", alignment=Qt.AlignCenter, styleSheet="border:1px solid #000")
        self.lbl_res = QLabel("Результат", alignment=Qt.AlignCenter, styleSheet="border:1px solid #000")
        lay.addWidget(self.lbl_orig, 2)
        lay.addWidget(self.lbl_res, 2)

    def dragEnterEvent(self, e): 
        e.accept() if e.mimeData().hasUrls() else e.ignore()

    def dropEvent(self, e):
        path = e.mimeData().urls()[0].toLocalFile()
        if path: self.open_file(path)

    def load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть", "", "Images (*.png *.jpg *.bmp)")
        if path: self.open_file(path)

    def open_file(self, path):
        try:
            self.img = self.p.load(path)
            self.res = self.img.copy()
            self.prev = None
            self.sp_w.setValue(self.img.width)
            self.sp_h.setValue(self.img.height)
            self.lbl_info.setText(f"Формат: {self.img.format}\nРазмер: {self.img.size}")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def apply(self):
        if not self.img: return
        self.prev = self.res
        self.res = self.p.process(self.img, self.chk.isChecked(), self.sld.value(), self.sp_w.value(), self.sp_h.value())
        self.refresh()

    def undo(self):
        if self.prev:
            self.res = self.prev
            self.prev = None
            self.refresh()

    def save(self):
        if not self.res: return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", "", "PNG (*.png);;JPEG (*.jpg)")
        if path:
            self.p.save(self.res, path)
            QMessageBox.information(self, "Готово", "Сохранено")

    def refresh(self):
        for lbl, img in [(self.lbl_orig, self.img), (self.lbl_res, self.res)]:
            if not img: continue
            data = img.convert("RGB").tobytes("raw", "RGB")
            qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
            lbl.setPixmap(QPixmap.fromImage(qimg).scaled(lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))