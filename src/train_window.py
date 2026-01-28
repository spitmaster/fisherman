from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QProgressBar, QTextEdit, QGroupBox, QGridLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import os
import subprocess
import shutil

class TrainThread(QThread):
    progress_updated = pyqtSignal(int)
    log_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, data_dir, model_path, epochs, batch_size, imgsz):
        super().__init__()
        self.data_dir = data_dir
        self.model_path = model_path
        self.epochs = epochs
        self.batch_size = batch_size
        self.imgsz = imgsz
    
    def run(self):
        try:
            # 创建数据配置文件
            data_yaml = os.path.join(self.data_dir, 'data.yaml')
            if not os.path.exists(data_yaml):
                self.log_updated.emit('错误: 数据目录中缺少 data.yaml 文件')
                self.finished.emit(False, '数据目录中缺少 data.yaml 文件')
                return
            
            # 构建训练命令
            command = [
                'python', '-m', 'ultralytics', 'train',
                '--data', data_yaml,
                '--model', self.model_path,
                '--epochs', str(self.epochs),
                '--batch', str(self.batch_size),
                '--imgsz', str(self.imgsz),
                '--project', 'runs/train',
                '--name', 'exp'
            ]
            
            self.log_updated.emit(f'开始训练: {" ".join(command)}')
            
            # 执行训练命令
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in iter(process.stdout.readline, ''):
                self.log_updated.emit(line.strip())
                # 尝试提取进度信息
                if '%' in line and 'Epoch' in line:
                    try:
                        progress = int(line.split('%')[0].split()[-1])
                        self.progress_updated.emit(progress)
                    except:
                        pass
            
            process.wait()
            
            if process.returncode == 0:
                self.log_updated.emit('训练完成！')
                self.finished.emit(True, '训练成功完成')
            else:
                self.log_updated.emit(f'训练失败，返回代码: {process.returncode}')
                self.finished.emit(False, f'训练失败，返回代码: {process.returncode}')
                
        except Exception as e:
            self.log_updated.emit(f'训练过程中出错: {e}')
            self.finished.emit(False, f'训练过程中出错: {e}')

class TrainWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('模型训练')
        self.setGeometry(200, 200, 900, 700)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # 创建数据准备区域
        data_group = QGroupBox('数据准备')
        data_layout = QGridLayout()
        
        data_layout.addWidget(QLabel('标注数据目录:'), 0, 0)
        self.data_dir = QLineEdit()
        data_layout.addWidget(self.data_dir, 0, 1)
        
        browse_button = QPushButton('浏览')
        browse_button.clicked.connect(self.browse_data_dir)
        data_layout.addWidget(browse_button, 0, 2)
        
        data_layout.addWidget(QLabel('提示:'), 1, 0)
        data_layout.addWidget(QLabel('请确保数据目录中包含标注好的图片和 data.yaml 配置文件'), 1, 1, 1, 2)
        
        data_group.setLayout(data_layout)
        
        # 创建训练参数区域
        params_group = QGroupBox('训练参数')
        params_layout = QGridLayout()
        
        params_layout.addWidget(QLabel('基础模型:'), 0, 0)
        self.model_path = QLineEdit('yolov8n.pt')
        params_layout.addWidget(self.model_path, 0, 1)
        
        params_layout.addWidget(QLabel('训练轮数:'), 1, 0)
        self.epochs = QSpinBox()
        self.epochs.setRange(1, 1000)
        self.epochs.setValue(50)
        params_layout.addWidget(self.epochs, 1, 1)
        
        params_layout.addWidget(QLabel('批量大小:'), 2, 0)
        self.batch_size = QSpinBox()
        self.batch_size.setRange(1, 64)
        self.batch_size.setValue(16)
        params_layout.addWidget(self.batch_size, 2, 1)
        
        params_layout.addWidget(QLabel('图像尺寸:'), 3, 0)
        self.imgsz = QSpinBox()
        self.imgsz.setRange(128, 1024)
        self.imgsz.setValue(640)
        self.imgsz.setSingleStep(32)
        params_layout.addWidget(self.imgsz, 3, 1)
        
        params_group.setLayout(params_layout)
        
        # 创建训练控制区域
        control_group = QGroupBox('训练控制')
        control_layout = QVBoxLayout()
        
        self.start_train_button = QPushButton('开始训练')
        self.start_train_button.clicked.connect(self.start_train)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        control_layout.addWidget(self.start_train_button)
        control_layout.addWidget(self.progress_bar)
        control_layout.addWidget(self.log_text)
        
        control_group.setLayout(control_layout)
        
        # 添加所有组件到主布局
        main_layout.addWidget(data_group)
        main_layout.addWidget(params_group)
        main_layout.addWidget(control_group)
        
        self.setLayout(main_layout)
        
        # 训练线程
        self.train_thread = None
    
    def browse_data_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, '选择数据目录')
        if dir_path:
            self.data_dir.setText(dir_path)
    
    def start_train(self):
        data_dir = self.data_dir.text().strip()
        model_path = self.model_path.text().strip()
        
        if not data_dir:
            QMessageBox.warning(self, '警告', '请选择数据目录')
            return
        
        if not os.path.exists(data_dir):
            QMessageBox.warning(self, '警告', '所选数据目录不存在')
            return
        
        if not model_path:
            QMessageBox.warning(self, '警告', '请输入模型路径')
            return
        
        # 禁用训练按钮
        self.start_train_button.setEnabled(False)
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        # 创建训练线程
        self.train_thread = TrainThread(
            data_dir=data_dir,
            model_path=model_path,
            epochs=self.epochs.value(),
            batch_size=self.batch_size.value(),
            imgsz=self.imgsz.value()
        )
        
        # 连接信号
        self.train_thread.progress_updated.connect(self.update_progress)
        self.train_thread.log_updated.connect(self.update_log)
        self.train_thread.finished.connect(self.train_finished)
        
        # 启动训练
        self.train_thread.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def update_log(self, text):
        self.log_text.append(text)
        # 自动滚动到底部
        self.log_text.ensureCursorVisible()
    
    def train_finished(self, success, message):
        # 启用训练按钮
        self.start_train_button.setEnabled(True)
        
        if success:
            QMessageBox.information(self, '信息', message)
        else:
            QMessageBox.warning(self, '警告', message)
