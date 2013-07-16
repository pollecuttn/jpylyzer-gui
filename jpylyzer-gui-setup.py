from cx_Freeze import setup, Executable

setup(
        name = "Jpylyzer GUI",
        version = "0.1",
        description = "GUI for jpylyzer",
        executables = [Executable("jpylyzergui.py")])
