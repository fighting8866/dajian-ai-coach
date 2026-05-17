import os
import shutil
import subprocess
import traceback
from uuid import uuid4


class PptConvertError(Exception):
    """PPT 转换异常"""


def convert_ppt_to_pptx(input_path: str, output_dir: str) -> str:
    """
    将 .ppt 转换为 .pptx；若输入已是 .pptx 则直接返回。
    优先尝试 PowerPoint COM，失败后尝试 LibreOffice。
    """
    if not input_path:
        raise PptConvertError("输入文件路径为空")

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".pptx":
        return input_path

    if ext != ".ppt":
        raise PptConvertError(f"不支持的文件类型: {ext}")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{uuid4().hex}.pptx")

    powerpoint_error = ""
    libreoffice_error = ""

    try:
        return _convert_by_powerpoint(input_path, output_path)
    except Exception as e:
        powerpoint_error = f"{repr(e)} | traceback: {traceback.format_exc()}"

    try:
        return _convert_by_libreoffice(input_path, output_dir)
    except Exception as e:
        libreoffice_error = f"{repr(e)} | traceback: {traceback.format_exc()}"

    raise RuntimeError(
        "当前环境无法自动转换 .ppt 文件。"
        f" PowerPoint 转换失败: {powerpoint_error};"
        f" LibreOffice 转换失败: {libreoffice_error}"
    )


def _convert_by_powerpoint(input_path: str, output_path: str) -> str:
    """
    使用 PowerPoint COM 自动化转换 .ppt -> .pptx。
    """
    app = None
    presentation = None
    pythoncom = None
    try:
        import pythoncom
        import win32com.client
    except Exception as e:
        raise PptConvertError(f"未安装或无法使用 pywin32: {repr(e)}")

    try:
        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(output_path)
        pythoncom.CoInitialize()
        app = win32com.client.DispatchEx("PowerPoint.Application")
        app.Visible = 0
        # WithWindow=False，避免弹窗干扰
        presentation = app.Presentations.Open(
            input_path,
            ReadOnly=1,
            Untitled=0,
            WithWindow=False,
        )
        # 24 = ppSaveAsOpenXMLPresentation (.pptx)
        presentation.SaveAs(output_path, 24)
    except Exception as e:
        raise PptConvertError(f"PowerPoint COM 转换异常: {repr(e)}")
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    if not os.path.exists(output_path):
        raise PptConvertError("PowerPoint 转换后未生成 .pptx 文件")
    if os.path.getsize(output_path) <= 0:
        raise PptConvertError("PowerPoint 转换后输出文件为空")
    return output_path


def _convert_by_libreoffice(input_path: str, output_dir: str) -> str:
    """
    使用 LibreOffice 命令行转换 .ppt -> .pptx。
    """
    soffice = shutil.which("soffice")
    if not soffice:
        raise PptConvertError("未找到 soffice 命令")

    cmd = [
        soffice,
        "--headless",
        "--convert-to",
        "pptx",
        "--outdir",
        output_dir,
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        raise PptConvertError(f"命令执行失败，stdout={stdout} stderr={stderr}")

    base_name = os.path.splitext(os.path.basename(input_path))[0]
    converted_path = os.path.join(output_dir, f"{base_name}.pptx")
    if not os.path.exists(converted_path):
        raise PptConvertError("LibreOffice 转换后未找到输出文件")
    if os.path.getsize(converted_path) <= 0:
        raise PptConvertError("LibreOffice 转换后输出文件为空")
    return converted_path
