import ctypes
import sys
import os

def test_c10_dll():
    """测试 c10.dll 是否可以加载"""
    try:
        # 获取 PyTorch 安装目录
        import torch
        torch_path = os.path.dirname(torch.__file__)
        print(f"PyTorch 安装路径: {torch_path}")
        
        dll_path = os.path.join(torch_path, "lib", "c10.dll")
        print(f"c10.dll 路径: {dll_path}")
        
        if not os.path.exists(dll_path):
            print("错误: c10.dll 不存在")
            return False
            
        # 尝试使用 ctypes 加载 dll
        print("尝试加载 c10.dll...")
        dll = ctypes.CDLL(dll_path)
        print("成功加载 c10.dll")
        
        return True
        
    except Exception as e:
        print(f"加载 c10.dll 失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return False

def list_dependencies():
    """列出系统依赖项"""
    import platform
    
    print(f"系统信息:")
    print(f"  操作系统: {platform.platform()}")
    print(f"  架构: {platform.machine()}")
    print(f"  Python 版本: {sys.version}")
    print(f"  可执行文件: {sys.executable}")
    print(f"  sys.path: {sys.path}")
    
    print("\nPATH 变量:")
    path_var = os.environ.get("PATH")
    if path_var:
        for i, path in enumerate(path_var.split(os.pathsep)[:10]):
            if os.path.exists(path):
                print(f"  [{i}] {path}")

def check_visual_cpp_redistributable():
    """检查 Visual C++ Redistributable"""
    print("\nVisual C++ Redistributable 检查:")
    
    if sys.platform == "win32":
        import winreg
        
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64")
            version = winreg.QueryValueEx(key, "Version")[0]
            installed = winreg.QueryValueEx(key, "Installed")[0]
            
            print(f"  Visual C++ Redistributable x64: 版本 {version}, 已安装: {'是' if installed else '否'}")
            
            if installed:
                print("  Visual C++ Redistributable x64 已正确安装")
            else:
                print("  警告: Visual C++ Redistributable x64 未正确安装")
                
        except Exception as e:
            print(f"  无法读取注册表: {e}")
            print("  请检查是否已安装 Visual C++ Redistributable for Visual Studio 2015-2022")

def main():
    print("=== PyTorch DLL 诊断工具 ===")
    print(f"日期: {__import__('datetime').datetime.now()}")
    print()
    
    # 列出系统信息
    list_dependencies()
    check_visual_cpp_redistributable()
    print()
    
    # 测试 c10.dll
    print("=== 测试 c10.dll ===")
    test_c10_dll()
    print()
    
    print("=== 诊断完成 ===")
    print()
    print("可能的解决方案:")
    print("1. 确保已安装 Visual C++ Redistributable for Visual Studio 2015-2022")
    print("2. 重新安装 PyTorch: pip uninstall torch torchvision torchaudio && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu")
    print("3. 检查系统依赖项是否损坏")

if __name__ == "__main__":
    main()