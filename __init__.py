from .asr_nodes import ASRMW
from .color_picker import ColorPickerMW
from .subtitles2video import StaticSubtitlesToVideoMW, DynamicSubtitlesToVideoMW



NODE_CLASS_MAPPINGS = {
    "ASRMW": ASRMW,
    "ColorPickerMW": ColorPickerMW,
    "StaticSubtitlesToVideoMW": StaticSubtitlesToVideoMW,
    "DynamicSubtitlesToVideoMW": DynamicSubtitlesToVideoMW,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ASRMW": "自动语音识别",
    "ColorPickerMW": "极简颜色选择器",
    "StaticSubtitlesToVideoMW": "视频添加静态字幕",
    "DynamicSubtitlesToVideoMW": "视频添加动态字幕",
}

WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
