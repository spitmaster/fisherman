import sys
print('Python version:', sys.version)
print('Python executable:', sys.executable)

try:
    import numpy
    print('NumPy version:', numpy.__version__)
except Exception as e:
    print('NumPy import error:', e)

try:
    import cv2
    print('OpenCV version:', cv2.__version__)
except Exception as e:
    print('OpenCV import error:', e)

try:
    import torch
    print('PyTorch version:', torch.__version__)
except Exception as e:
    print('PyTorch import error:', e)

try:
    from PyQt5.QtWidgets import QApplication
    print('PyQt5 imported successfully')
except Exception as e:
    print('PyQt5 import error:', e)
