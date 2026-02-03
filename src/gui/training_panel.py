import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from PIL import Image, ImageTk
import threading
import time
from training.data_manager import DataManager
from training.model_trainer import ModelTrainer

class TrainingPanel:
    """训练模块面板"""
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.frame = ttk.Frame(parent_frame)
        
        # 数据管理器
        self.data_manager = DataManager()
        
        # 当前显示的图像
        self.current_image = None
        self.current_image_path = None
        self.current_annotations = []
        self.image_list = []
        self.current_image_index = 0
        
        # 标注状态
        self.is_annotating = False
        self.start_x = 0
        self.start_y = 0
        self.current_bbox = None
        
        # 初始化UI
        self._init_ui()
        self._update_image_list()
        self._update_class_list()
    
    def _init_ui(self):
        """初始化UI"""
        # 创建主布局
        main_frame = ttk.Frame(self.frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧面板 - 图像显示和标注
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 图像显示区域
        image_frame = ttk.LabelFrame(left_panel, text="图像标注", padding=10)
        image_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(image_frame, bg="gray", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标事件用于标注
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        
        # 图像控制按钮
        control_frame = ttk.Frame(image_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="上一张", command=self._prev_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="下一张", command=self._next_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="保存标注", command=self._save_annotation).pack(side=tk.LEFT, padx=5)
        
        # 右侧面板 - 控制和信息
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # 数据导入区域
        import_frame = ttk.LabelFrame(right_panel, text="数据导入", padding=10)
        import_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(import_frame, text="导入图像", command=self._import_images).pack(fill=tk.X, pady=5)
        ttk.Button(import_frame, text="导入文件夹", command=self._import_folder).pack(fill=tk.X, pady=5)
        
        # 类别管理区域
        class_frame = ttk.LabelFrame(right_panel, text="类别管理", padding=10)
        class_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.class_listbox = tk.Listbox(class_frame, height=8)
        self.class_listbox.pack(fill=tk.BOTH, expand=True)
        
        class_input_frame = ttk.Frame(class_frame)
        class_input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.class_entry = ttk.Entry(class_input_frame)
        self.class_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(class_input_frame, text="添加", command=self._add_class).pack(side=tk.RIGHT)
        
        # 训练控制区域
        train_frame = ttk.LabelFrame(right_panel, text="模型训练", padding=10)
        train_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(train_frame, text="基础模型:").pack(anchor=tk.W)
        self.base_model_combo = ttk.Combobox(train_frame, values=["yolov8n.pt", "yolov8s.pt", "yolov8m.pt"])
        self.base_model_combo.pack(fill=tk.X, pady=(0, 5))
        self.base_model_combo.set("yolov8n.pt")
        
        ttk.Label(train_frame, text="训练轮数:").pack(anchor=tk.W)
        self.epochs_entry = ttk.Entry(train_frame)
        self.epochs_entry.pack(fill=tk.X, pady=(0, 5))
        self.epochs_entry.insert(0, "50")
        
        ttk.Button(train_frame, text="开始训练", command=self._start_training).pack(fill=tk.X, pady=5)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(right_panel, text="训练进度", padding=10)
        progress_frame.pack(fill=tk.X)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X)
        
        self.progress_label = ttk.Label(progress_frame, text="准备就绪")
        self.progress_label.pack(fill=tk.X, pady=(5, 0))
    
    def _update_image_list(self):
        """更新图像列表"""
        self.image_list = self.data_manager.get_image_list()
        self.current_image_index = 0
        if self.image_list:
            self._load_current_image()
    
    def _update_class_list(self):
        """更新类别列表"""
        self.class_listbox.delete(0, tk.END)
        for class_name in self.data_manager.classes:
            self.class_listbox.insert(tk.END, class_name)
    
    def _import_images(self):
        """导入图像"""
        file_paths = filedialog.askopenfilenames(
            title="选择图像文件",
            filetypes=[("图像文件", "*.png *.jpg *.jpeg *.bmp *.tiff")]
        )
        
        if file_paths:
            imported_files = self.data_manager.import_images(file_paths, copy=True)
            self._update_image_list()
            messagebox.showinfo("导入", f"成功导入 {len(imported_files)} 张图像")
    
    def _import_folder(self):
        """导入文件夹"""
        folder_path = filedialog.askdirectory(title="选择图像文件夹")
        
        if folder_path:
            image_files = []
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                    image_files.append(os.path.join(folder_path, filename))
            
            imported_files = self.data_manager.import_images(image_files, copy=True)
            self._update_image_list()
            messagebox.showinfo("导入", f"成功导入 {len(imported_files)} 张图像")
    
    def _add_class(self):
        """添加类别"""
        class_name = self.class_entry.get().strip()
        if class_name:
            self.data_manager.add_class(class_name)
            self._update_class_list()
            self.class_entry.delete(0, tk.END)
    
    def _prev_image(self):
        """上一张图像"""
        if self.image_list and self.current_image_index > 0:
            self.current_image_index -= 1
            self._load_current_image()
    
    def _next_image(self):
        """下一张图像"""
        if self.image_list and self.current_image_index < len(self.image_list) - 1:
            self.current_image_index += 1
            self._load_current_image()
    
    def _save_annotation(self):
        """保存标注"""
        if self.current_annotations and self.current_image_path:
            try:
                image_filename = os.path.basename(self.current_image_path)
                self.data_manager.save_annotation(image_filename, self.current_annotations)
                messagebox.showinfo("保存", f"保存了 {len(self.current_annotations)} 个标注")
            except Exception as e:
                messagebox.showerror("错误", f"保存标注失败: {e}")
        else:
            messagebox.showwarning("警告", "没有标注需要保存")
    
    def _start_training(self):
        """开始训练"""
        # 检查数据准备情况
        dataset_info = self.data_manager.get_dataset_info()
        if dataset_info['total_images'] == 0:
            messagebox.showwarning("警告", "没有导入任何图像")
            return
        
        if dataset_info['annotated_images'] == 0:
            messagebox.showwarning("警告", "没有图像被标注")
            return
        
        if dataset_info['classes_count'] == 0:
            messagebox.showwarning("警告", "没有定义任何类别")
            return
        
        try:
            epochs = int(self.epochs_entry.get())
            base_model = self.base_model_combo.get()
            
            # 分割数据集
            self.data_manager.split_dataset()
            
            # 开始训练
            self.progress_bar.start(10)
            self.progress_label.config(text="训练中...")
            
            def train_task():
                try:
                    trainer = ModelTrainer()
                    dataset_yaml = os.path.join(self.data_manager.data_dir, "dataset.yaml")
                    result = trainer.train(dataset_yaml, base_model)
                    
                    self.frame.after(0, lambda: self._training_completed(result))
                except Exception as e:
                    self.frame.after(0, lambda: self._training_failed(e))
            
            thread = threading.Thread(target=train_task, daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"训练准备失败: {e}")
    
    def _training_completed(self, result):
        """训练完成"""
        self.progress_bar.stop()
        self.progress_label.config(text="训练完成")
        best_model_path = result.get('best_model_path', '未找到最佳模型')
        messagebox.showinfo("训练", f"模型训练完成\n最佳模型: {best_model_path}")
    
    def _training_failed(self, error):
        """训练失败"""
        self.progress_bar.stop()
        self.progress_label.config(text="训练失败")
        messagebox.showerror("训练失败", f"训练过程中出错: {str(error)}")
    
    def _on_mouse_down(self, event):
        """鼠标按下事件"""
        if self.current_image:
            self.is_annotating = True
            self.start_x = event.x
            self.start_y = event.y
            self.current_bbox = None
    
    def _on_mouse_drag(self, event):
        """鼠标拖动事件"""
        if self.is_annotating and self.current_bbox:
            self.canvas.delete(self.current_bbox)
        
        if self.is_annotating:
            self.current_bbox = self.canvas.create_rectangle(
                self.start_x, self.start_y, event.x, event.y,
                outline="red", width=2
            )
    
    def _on_mouse_up(self, event):
        """鼠标释放事件"""
        if self.is_annotating:
            self.is_annotating = False
            
            # 获取标注坐标
            x1 = min(self.start_x, event.x)
            y1 = min(self.start_y, event.y)
            x2 = max(self.start_x, event.x)
            y2 = max(self.start_y, event.y)
            
            # 这里需要处理标注数据
            if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:  # 最小尺寸检查
                # 获取选中的类别
                selected_index = self.class_listbox.curselection()
                class_id = 0
                if selected_index:
                    class_id = selected_index[0]
                
                # 添加标注到列表
                annotation = {
                    'bbox': [x1, y1, x2, y2],
                    'class_id': class_id
                }
                self.current_annotations.append(annotation)
                
                # 绘制永久标注框
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="green", width=2)
    
    def _load_current_image(self):
        """加载当前图像"""
        if not self.image_list:
            return
        
        image_filename = self.image_list[self.current_image_index]
        image_path = os.path.join(self.data_manager.images_dir, image_filename)
        self.load_image(image_path)
        
        # 加载标注
        self.current_annotations = self.data_manager.load_annotation(image_filename)
        self._draw_annotations()
    
    def _draw_annotations(self):
        """绘制标注框"""
        if not self.current_image:
            return
        
        # 获取图像缩放比例
        img_width, img_height = self.current_image.size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            width_ratio = canvas_width / img_width
            height_ratio = canvas_height / img_height
            scale = min(width_ratio, height_ratio) * 0.9
            
            for ann in self.current_annotations:
                bbox = ann['bbox']
                x1, y1, x2, y2 = bbox
                
                # 计算图像在画布上的位置和缩放
                display_width = int(img_width * scale)
                display_height = int(img_height * scale)
                x_offset = (canvas_width - display_width) // 2
                y_offset = (canvas_height - display_height) // 2
                
                # 缩放标注框坐标
                x1_scaled = x_offset + int(x1 * scale)
                y1_scaled = y_offset + int(y1 * scale)
                x2_scaled = x_offset + int(x2 * scale)
                y2_scaled = y_offset + int(y2 * scale)
                
                # 绘制标注框
                color = "blue"
                if 'class_id' in ann:
                    class_id = ann['class_id']
                    colors = ["blue", "red", "green", "orange", "purple"]
                    color = colors[class_id % len(colors)]
                
                self.canvas.create_rectangle(x1_scaled, y1_scaled, x2_scaled, y2_scaled, 
                                             outline=color, width=2)
    
    def load_image(self, image_path):
        """加载图像到画布"""
        try:
            # 清除画布
            self.canvas.delete("all")
            
            # 加载图像
            image = Image.open(image_path)
            
            # 调整图像大小以适应画布
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # 计算缩放比例
                img_width, img_height = image.size
                width_ratio = canvas_width / img_width
                height_ratio = canvas_height / img_height
                scale = min(width_ratio, height_ratio) * 0.9  # 保留10%边距
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 显示图像
            self.photo = ImageTk.PhotoImage(image)
            self.canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=self.photo, anchor=tk.CENTER
            )
            
            self.current_image = image
            self.current_image_path = image_path
            
        except Exception as e:
            messagebox.showerror("错误", f"加载图像失败: {e}")
    
    def get_frame(self):
        """获取面板框架"""
        return self.frame