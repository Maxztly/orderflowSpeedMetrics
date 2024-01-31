import sys
import threading
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QTextEdit
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtGui import QIcon
from PIL import ImageGrab
import time

class FullscreenSelection:
    def __init__(self):
        self.selection = None

    def show(self):
        import tkinter as tk
        self.root = tk.Tk()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.3)
        self.canvas = tk.Canvas(self.root, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.mainloop()
        return self.selection

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 0, 0, outline="red")

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        self.selection = (self.start_x, self.start_y, event.x, event.y)
        self.root.quit()
        self.root.destroy()

def has_pixel_changes(image1, image2):
    if image1.size != image2.size:
        raise ValueError("Bilder müssen dieselbe Größe haben.")
    arr1 = np.array(image1)
    arr2 = np.array(image2)
    return np.any(arr1 != arr2)


class MainUI(QMainWindow):
    text_update_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORDERFLOWSPEED")
        self.resize(200, 1368)

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #000000;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #555555;
                color: #FFFFFF;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 16px;
                margin: 5px;
            }
            QTextEdit {
                background-color: #333333;
                color: #FFFFFF;
                font-size: 16px;
                margin-bottom: 10px;
                border-radius: 5px;
                padding: 10px;
            }
            QTextEdit#two_sec {
                color: red;
                font-weight: bold;
                font-size: 20px;
            }
            QTextEdit#five_sec {
                color: yellow;
                font-weight: bold;
                font-size: 20px;
            }
            QTextEdit#ten_sec {
                color: green;
                font-weight: bold;
                font-size: 20px;
            }
            """
        )

        screen_geometry = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        self.move(window_geometry.topLeft())

        self.main_widget = QWidget(self)
        self.main_layout = QVBoxLayout(self.main_widget)

        self.start_button = QPushButton("start monitoring", self)
        self.start_button.clicked.connect(self.start_monitoring)
        self.main_layout.addWidget(self.start_button)
 
        self.name_layout = QLabel("      2s              5s            0.1m", self)
        self.name_layout.setStyleSheet("color: #FFFFFF;")
        self.main_layout.addWidget(self.name_layout)

        self.intervals_layout = QHBoxLayout()

        self.output_text_2s = QTextEdit(self)
        self.output_text_2s.setObjectName("two_sec")  
        self.output_text_2s.setReadOnly(True)
        self.intervals_layout.addWidget(self.output_text_2s)

        self.output_text_5s = QTextEdit(self)
        self.output_text_5s.setObjectName("five_sec")  
        self.output_text_5s.setReadOnly(True)
        self.intervals_layout.addWidget(self.output_text_5s)

        self.output_text_10s = QTextEdit(self)
        self.output_text_10s.setObjectName("ten_sec")
        self.output_text_10s.setReadOnly(True)
        self.intervals_layout.addWidget(self.output_text_10s)

        self.main_layout.addLayout(self.intervals_layout)
        self.setCentralWidget(self.main_widget)
        self.text_update_signal.connect(self.update_output)

        self.clear_button = QPushButton("clear data", self)
        self.clear_button.clicked.connect(self.clear_data)
        self.main_layout.addWidget(self.clear_button)

        font = QFont()
        font.setPointSize(16)

        self.name_layout.setFont(font)
        self.output_text_2s.setFont(font)
        self.output_text_5s.setFont(font)
        self.output_text_10s.setFont(font)
        self.clear_button.setFont(font)
        self.start_button.setFont(font)

    @pyqtSlot(str)
    def update_output(self, text):
        interval, avg_changes = text.split(':')
        new_text = f"{avg_changes}\n"
        text_edit = self.get_text_edit_by_interval(interval)
        text_edit.moveCursor(QTextCursor.Start)
        text_edit.insertPlainText(new_text)
        text_edit.moveCursor(QTextCursor.Start)

    def get_text_edit_by_interval(self, interval):
        return {
            '2': self.output_text_2s,
            '5': self.output_text_5s,
            '10': self.output_text_10s,
        }[interval]

    def start_monitoring(self):
        monitor_thread = threading.Thread(target=self.monitor)
        monitor_thread.daemon = True
        monitor_thread.start()

    def monitor(self):
        selector = FullscreenSelection()
        selection = selector.show()

        if selection:
            x1, y1, x2, y2 = selection
            previous_image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            changes_over_time = {2: [], 5: [], 10: []}
            start_times = {2: time.time(), 5: time.time(), 10: time.time()}

            try:
                while True:
                    current_image = ImageGrab.grab(bbox=(x1, y1, x2, y2))
                    change_detected = has_pixel_changes(previous_image, current_image)
                    for interval in changes_over_time:
                        changes_over_time[interval].append(int(change_detected))
                        if time.time() - start_times[interval] >= interval:
                            avg_changes = np.mean(changes_over_time[interval])
                            self.text_update_signal.emit(f"{interval}:{avg_changes:.2f}")
                            changes_over_time[interval] = []
                            start_times[interval] = time.time()

                    previous_image = current_image
                    time.sleep(0.001)
            except Exception as e:
                error_msg = str(e)
                for interval in changes_over_time:
                    self.text_update_signal.emit(f"{interval}:{error_msg}")

    def clear_data(self):
        self.output_text_2s.clear()
        self.output_text_5s.clear()
        self.output_text_10s.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = MainUI()

    icon_path = "mainicon.ico"
    app_icon = QIcon(icon_path)

    ui.setWindowIcon(app_icon)

    ui.show()
    sys.exit(app.exec_())