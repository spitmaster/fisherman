import sys
print('Python version:', sys.version)

try:
    from PyQt5.QtWidgets import QApplication, QWidget, QLabel
    print('PyQt5导入成功')
except Exception as e:
    print('PyQt5导入失败:', e)

try:
    from ultralytics import YOLO
    print('Ultralytics导入成功')
except Exception as e:
    print('Ultralytics导入失败:', e)

print('测试完成')
