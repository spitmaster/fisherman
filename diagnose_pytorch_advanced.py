import os
import sys
import ctypes
import subprocess
import platform
import tempfile
from pathlib import Path

def print_system_info():
    """打印详细的系统信息"""
    print("="*60)
    print("系统信息")
    print("="*60)
    print(f"操作系统: {platform.platform()}")
    print(f"架构: {platform.machine()}")
    print(f"处理器: {platform.processor()}")
    print(f"Python版本: {sys.version}")
    print(f"版本信息: {sys.version_info}")
    print(f"可执行文件: {sys.executable}")
    print(f"当前工作目录: {os.getcwd()}")
    print()

def check_torch_installation():
    """检查PyTorch安装"""
    print("="*60)
    print("PyTorch安装检查")
    print("="*60)
    
    try:
        import torch
        print(f"PyTorch版本: {torch.__version__}")
        print(f"安装路径: {os.path.dirname(torch.__file__)}")
        print(f"CUDA支持: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"CUDA版本: {torch.version.cuda}")
            print(f"GPU设备数: {torch.cuda.device_count()}")
            print(f"当前设备: {torch.cuda.get_device_name(torch.cuda.current_device())}")
        print()
        return torch
    except Exception as e:
        print(f"PyTorch导入失败: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        print()
        return None

def check_dll_dependencies(dll_path):
    """检查DLL的依赖关系"""
    print(f"检查依赖项: {dll_path}")
    
    # 使用Dependency Walker或类似工具检查DLL依赖
    # 这里我们使用dumpbin工具（Visual Studio工具）
    dumpbin_path = r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.32.31326\bin\Hostx64\x64\dumpbin.exe"
    
    if os.path.exists(dumpbin_path):
        try:
            result = subprocess.run(
                [dumpbin_path, "/dependents", dll_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            print(f"依赖项分析结果:\n{result.stdout}")
            if result.stderr:
                print(f"错误信息:\n{result.stderr}")
        except Exception as e:
            print(f"使用dumpbin分析依赖项失败: {e}")
    else:
        print("未找到dumpbin工具，无法检查DLL依赖项")
    print()

def test_c10_dll():
    """测试c10.dll是否可以加载"""
    print("="*60)
    print("c10.dll加载测试")
    print("="*60)
    
    try:
        import torch
        torch_path = os.path.dirname(torch.__file__)
        c10_path = os.path.join(torch_path, "lib", "c10.dll")
        
        if not os.path.exists(c10_path):
            print(f"错误: c10.dll不存在于路径 {c10_path}")
            return False
        
        print(f"c10.dll路径: {c10_path}")
        print(f"文件大小: {os.path.getsize(c10_path)}字节")
        print(f"存在性: {os.path.exists(c10_path)}")
        
        # 检查文件权限
        import stat
        st = os.stat(c10_path)
        print(f"文件权限: {oct(st.st_mode & 0o777)}")
        
        # 尝试使用ctypes加载DLL
        try:
            dll = ctypes.CDLL(c10_path)
            print("✅ c10.dll加载成功")
            return True
        except Exception as e:
            print(f"❌ c10.dll加载失败: {e}")
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
            
            # 尝试检查DLL依赖项
            print()
            check_dll_dependencies(c10_path)
            
            return False
            
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return False
    print()

def check_system_path():
    """检查系统路径"""
    print("="*60)
    print("系统路径检查")
    print("="*60)
    
    path_var = os.environ.get("PATH", "")
    paths = path_var.split(os.pathsep)
    
    print("PATH环境变量包含以下目录:")
    for i, path in enumerate(paths):
        if path:
            exists = os.path.exists(path)
            print(f"  [{i}] {path} - {'✅' if exists else '❌'}")
    print()
    
    # 检查PyTorch库路径是否在系统路径中
    try:
        import torch
        torch_path = os.path.dirname(torch.__file__)
        lib_path = os.path.join(torch_path, "lib")
        print(f"PyTorch库路径: {lib_path}")
        print(f"PyTorch库路径是否在PATH中: {'✅' if lib_path in paths else '❌'}")
        
        if lib_path not in paths:
            print("警告: PyTorch库路径未在系统PATH中，可能导致DLL加载失败")
            print(f"建议添加: set PATH={lib_path};%PATH%")
            
    except Exception as e:
        print(f"无法获取PyTorch安装信息: {e}")
    print()

def check_visual_cpp_redistributable():
    """检查Visual C++ Redistributable"""
    print("="*60)
    print("Visual C++ Redistributable检查")
    print("="*60)
    
    if platform.system() == "Windows":
        import winreg
        
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                              r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64")
            version = winreg.QueryValueEx(key, "Version")[0]
            installed = winreg.QueryValueEx(key, "Installed")[0]
            
            print(f"Visual C++ Redistributable x64: 版本 {version}")
            print(f"已安装: {'✅' if installed else '❌'}")
            
            if installed:
                print("Visual C++ Redistributable x64 已正确安装")
            else:
                print("警告: Visual C++ Redistributable x64 未正确安装")
                
        except Exception as e:
            print(f"无法读取Visual C++ Redistributable注册表信息: {e}")
            print("请确保已安装Visual C++ Redistributable for Visual Studio 2015-2022")
    else:
        print("Visual C++ Redistributable仅适用于Windows系统")
    print()

def test_python_dll_load():
    """测试Python DLL加载"""
    print("="*60)
    print("Python DLL加载测试")
    print("="*60)
    
    try:
        # 尝试加载一些系统DLL
        test_dlls = [
            "kernel32.dll",
            "user32.dll",
            "gdi32.dll",
            "ole32.dll",
            "oleaut32.dll",
            "msvcp140.dll",
            "vcruntime140.dll",
            "vcruntime140_1.dll"
        ]
        
        for dll_name in test_dlls:
            try:
                dll = ctypes.WinDLL(dll_name)
                print(f"✅ {dll_name} 加载成功")
            except Exception as e:
                print(f"❌ {dll_name} 加载失败: {e}")
    except Exception as e:
        print(f"测试过程中出错: {e}")
    print()

def main():
    """主诊断函数"""
    print("PyTorch DLL初始化失败诊断工具")
    print("="*60)
    print()
    
    print_system_info()
    check_torch_installation()
    check_visual_cpp_redistributable()
    check_system_path()
    test_python_dll_load()
    test_c10_dll()
    
    print()
    print("="*60)
    print("诊断完成")
    print("="*60)
    print()
    
    print("可能的解决方案:")
    print("1. 确保已安装Visual C++ Redistributable for Visual Studio 2015-2022")
    print("2. 检查系统是否缺少必要的DLL文件")
    print("3. 尝试重新安装PyTorch:")
    print("   pip uninstall torch torchvision torchaudio")
    print("   pip install torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cpu")
    print("4. 检查PyTorch库路径是否在系统PATH中")
    print("5. 尝试使用conda安装PyTorch")
    print("6. 检查系统是否有病毒或安全软件阻止DLL加载")
    print()
    print("如果问题仍然存在，请考虑:")
    print("- 检查系统事件日志")
    print("- 使用Process Monitor跟踪DLL加载过程")
    print("- 重新安装Python和所有依赖库")

if __name__ == "__main__":
    main()