#!/usr/bin/env python3
"""构建可执行文件"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_executable():
    """使用PyInstaller构建可执行文件"""
    
    # 项目根目录
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    
    # 清理之前的构建
    build_dir = project_root / "build"
    dist_dir = project_root / "dist"
    spec_file = project_root / "fisherman.spec"
    
    for path in [build_dir, dist_dir, spec_file]:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
    
    # 准备PyInstaller命令
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Fisherman",
        "--onefile",
        "--windowed",  # 不显示控制台窗口
        "--icon=assets/icon.ico" if (project_root / "assets" / "icon.ico").exists() else "",
        "--add-data=src;src",
        "--add-data=requirements.txt;.",
        "--hidden-import=ultralytics",
        "--hidden-import=ultralytics.yolo",
        "--hidden-import=ultralytics.yolo.v8",
        "--hidden-import=torch",
        "--hidden-import=torchvision",
        "--hidden-import=cv2",
        "--hidden-import=PIL",
        "--hidden-import=PIL._imaging",
        "--hidden-import=pygetwindow",
        "--hidden-import=pyautogui",
        "--hidden-import=mss",
        "--hidden-import=sqlite3",
        "--hidden-import=tkinter",
        "--collect-all=ultralytics",
        "--collect-all=torch",
        "--collect-all=torchvision",
        "--clean",
        "--noconfirm",
        str(src_dir / "main.py")
    ]
    
    # 移除空字符串参数
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]
    
    print("运行PyInstaller命令:")
    print(" ".join(pyinstaller_cmd))
    
    # 运行PyInstaller
    try:
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        print("PyInstaller输出:")
        print(result.stdout)
        if result.stderr:
            print("错误:")
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller失败: {e}")
        print(f"标准错误: {e.stderr}")
        return False
    
    # 检查可执行文件是否创建成功
    exe_path = dist_dir / "Fisherman.exe"
    if exe_path.exists():
        print(f"\n✓ 可执行文件创建成功: {exe_path}")
        print(f"文件大小: {exe_path.stat().st_size / (1024*1024):.2f} MB")
        
        # 复制必要的资源文件
        resources = [
            "README.md",
            "LICENSE",
            "requirements.txt"
        ]
        
        for resource in resources:
            src = project_root / resource
            if src.exists():
                dst = dist_dir / resource
                shutil.copy2(src, dst)
                print(f"✓ 复制资源文件: {resource}")
        
        # 创建示例数据目录
        data_dirs = ["train_data", "models", "exports"]
        for data_dir in data_dirs:
            dir_path = dist_dir / data_dir
            dir_path.mkdir(exist_ok=True)
            (dir_path / ".gitkeep").touch()
            print(f"✓ 创建数据目录: {data_dir}")
        
        return True
    else:
        print("\n✗ 可执行文件创建失败")
        return False

def create_installer():
    """创建安装程序（可选）"""
    print("\n创建安装程序...")
    
    # 这里可以添加使用Inno Setup或NSIS创建安装程序的代码
    # 暂时只输出提示信息
    print("安装程序创建功能需要额外的工具:")
    print("1. Inno Setup (推荐)")
    print("2. NSIS")
    print("3. WiX Toolset")
    print("\n您可以手动创建安装程序，或直接分发dist目录中的文件。")

def main():
    """主函数"""
    print("=" * 60)
    print("Fisherman - 物体晃动监控系统 打包工具")
    print("=" * 60)
    
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
        print("✓ PyInstaller 已安装")
    except ImportError:
        print("✗ PyInstaller 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller 安装完成")
    
    # 构建可执行文件
    if build_executable():
        print("\n" + "=" * 60)
        print("构建成功！")
        print("=" * 60)
        print("\n下一步:")
        print("1. 可执行文件位于: dist/Fisherman.exe")
        print("2. 可以将其复制到任何Windows计算机上运行")
        print("3. 确保目标计算机已安装必要的Visual C++ Redistributable")
        print("4. 首次运行时可能需要等待模型下载")
        
        # 询问是否创建安装程序
        create_installer_response = input("\n是否创建安装程序？(y/N): ")
        if create_installer_response.lower() == 'y':
            create_installer()
    else:
        print("\n" + "=" * 60)
        print("构建失败！")
        print("=" * 60)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())