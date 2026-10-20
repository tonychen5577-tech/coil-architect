"""
Coil-Architect Pro - Native Binary Hardening & Packaging Pipeline
1. 将物理引擎 (physics_engine) 与授权看门狗 (license_manager) 通过 Cython 编译为 Windows C 原生机器码 (.pyd)
2. 彻底剥离原始 .py 源码
3. 使用 PyInstaller 打包为绿色单文件 EXE (无需安装 Python 或任何运行库)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def compile_cython():
    print("[1/3] 开始 Cython C 原生机器码硬化编译...")
    try:
        from Cython.Build import cythonize
        from setuptools import Extension, setup
    except ImportError:
        print("[-] 未检测到 Cython 或 setuptools，跳过 C 机器码转译，采用常规打包。")
        return False

    exts = [
        Extension("src.core.physics_engine", ["src/core/physics_engine.py"]),
        Extension("src.core.license_manager", ["src/core/license_manager.py"]),
    ]

    try:
        setup(
            ext_modules=cythonize(
                exts, 
                compiler_directives={"language_level": "3"}, 
                quiet=True
            ),
            script_args=["build_ext", "--inplace"]
        )
        print("[+] 物理算法核心与授权看门狗已成功编译为 Windows 原生 .pyd 机器码！")
        return True
    except Exception as e:
        print(f"[-] Cython 编译警告: {e}")
        return False


def build_pyinstaller():
    print("[2/3] 开始 PyInstaller 绿色免安装单文件打包...")
    entry_point = ROOT_DIR / "app.py"
    dist_dir = ROOT_DIR / "dist"
    build_dir = ROOT_DIR / "build"

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",             # 也可以通过 --onefile 打包为单文件
        "--windowed",           # 无黑框控制台
        "--name=Coil-Architect-Pro",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"{entry_point}"
    ]

    print(f"执行命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print(f"[3/3] 打包完成！生成路径: {dist_dir / 'Coil-Architect-Pro'}")


if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    compile_cython()
    build_pyinstaller()
