import os
import torch
import numpy as np
import tempfile
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip, ImageSequenceClip
import folder_paths
import langid
import re

cache_dir = folder_paths.get_temp_directory()
PUNCTUATION = "＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃『』【】〖〗〘〙〚〛〜〝〞〟–—‘’‛„‟…‧﹏." \
              "!?(),;:[]{}<>\"+-=&^*%$#@/" \
              "。？！，、；：“”‘'《》〈〉「」〔〕——·~`-"

def reverse_convert_to_list(text):
    
    pattern = r"\((\d+\.\d+),\s*(\d+\.\d+)\)\s*(.*)"
    result = []
    
    for line in text.strip().split("\n"):
        match = re.match(pattern, line)
        if match:
            start = float(match.group(1))
            end = float(match.group(2))
            content = match.group(3)
            result.append([start, end, content])
    
    return result

def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def parse_margin(margin_str: str, default_margin: int):
    if not margin_str: return (default_margin, default_margin)
    try:
        parts = [int(p.strip()) for p in margin_str.split(',')]
        if len(parts) == 1: return (parts[0], parts[0])
        if len(parts) == 2: return tuple(parts)
        if len(parts) == 4: return tuple(parts)
    except (ValueError, IndexError): pass
    return (default_margin, default_margin)

def get_font_list():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    font_dir = os.path.join(current_dir, "fonts")
    font_files = []
    if os.path.exists(font_dir):
        for file in os.listdir(font_dir):
            if file.lower().endswith(('.ttf', '.otf', '.ttc')):
                font_files.append(file)
    return font_files

def clean_punctuation_from_subtitles(subtitles, lang='en'):
    APOS_PLACEHOLDER = '¤'
    HYPHEN_PLACEHOLDER = '§'

    punct_nuke_pattern = re.compile(f"[{re.escape(PUNCTUATION)}]+")
    
    cleaned_subtitles = []
    for start, end, text in subtitles:
        if lang == 'en':
            
            processed_text = re.sub(r"(?<=[a-zA-Z])['’‘](?=[a-zA-Z])", APOS_PLACEHOLDER, text)
            processed_text = re.sub(r"(?<=[a-zA-Z0-9])-(?=[a-zA-Z0-9])", HYPHEN_PLACEHOLDER, processed_text)
            processed_text = punct_nuke_pattern.sub(" ", processed_text)

            processed_text = processed_text.replace(APOS_PLACEHOLDER, "'")
            processed_text = processed_text.replace(HYPHEN_PLACEHOLDER, "-")
        else:
            
            processed_text = punct_nuke_pattern.sub(" ", text)

        cleaned_text = re.sub(r'\s+', ' ', processed_text).strip()
        
        if cleaned_text:
            cleaned_subtitles.append((start, end, cleaned_text))
            
    return cleaned_subtitles



# ==============================================================================
#  NODE 1: STATIC SUBTITLES
# ==============================================================================

def smart_wrap_static(text, max_width_for_wrapping, font, font_size, language='en', stroke_width=0):
    if not text.strip(): return ""

    if language == 'zh': 
        lines, current_line = [], ''
        for char in text:
            test_line = f"{current_line}{char}"
            line_width = TextClip(text=test_line, font=font, font_size=font_size, stroke_width=stroke_width, method='label').w
            if line_width <= max_width_for_wrapping: current_line = test_line
            else: lines.append(current_line); current_line = char
        lines.append(current_line)
        corrected_lines = list(lines)
        for i in range(1, len(corrected_lines)):
            while corrected_lines[i] and corrected_lines[i][0] in PUNCTUATION:
                p = corrected_lines[i][0]
                if corrected_lines[i-1]: corrected_lines[i-1] += p; corrected_lines[i] = corrected_lines[i][1:]
                else: break
        return '\n'.join([line for line in corrected_lines if line.strip()])
    else: 
        words = text.split(' ')
        lines, current_line_words = [], []
        for word in words:
            if not word: continue
            temp_line_words = current_line_words + [word]
            test_line = " ".join(temp_line_words)
            line_width = TextClip(text=test_line, font=font, font_size=font_size, stroke_width=stroke_width, method='label').w
            if line_width <= max_width_for_wrapping: current_line_words.append(word)
            else:
                if word and word[0] in PUNCTUATION and len(current_line_words) > 0:
                    word_to_move = current_line_words.pop()
                    lines.append(" ".join(current_line_words))
                    current_line_words = [word_to_move, word]
                else:
                    lines.append(" ".join(current_line_words))
                    current_line_words = [word]
        if current_line_words: lines.append(" ".join(current_line_words))
        return '\n'.join([line for line in lines if line.strip()])

def create_static_subtitle_clip(text, start_time, end_time, video_width, video_height, **kwargs):
    font_size = kwargs.get('font_size', 24)
    font_path = kwargs.get('font_path', 'msyh.ttc')
    font_color = kwargs.get('font_color', (255, 255, 255))
    bg_color = kwargs.get('bg_color', (0, 0, 0))
    bg_opacity = kwargs.get('bg_opacity', 0.5)
    stroke_color = kwargs.get('stroke_color', font_color)
    stroke_width = kwargs.get('stroke_width', 1.0)
    interline = kwargs.get('interline', 4)
    margin_str = kwargs.get('margin_tuple', '')
    text_align = kwargs.get('text_align', 'left')
    block_horizontal_align = kwargs.get('block_horizontal_align', 'center')
    vertical_pos_offset = kwargs.get('vertical_pos_offset', 0)
    line_width_ratio = kwargs.get('line_width_ratio', 0.8)
    language = kwargs.get('language', 'en')

    allowed_width = int(video_width * line_width_ratio)
    wrapped_text = smart_wrap_static(text, allowed_width, font_path, font_size, language, stroke_width)

    if not wrapped_text.strip():
        return ColorClip(size=(1, 1), color=(0,0,0), duration=end_time-start_time).with_opacity(0).with_start(start_time)

    bg_color_with_alpha = bg_color + (int(bg_opacity * 255),)
    default_inner_margin = int(font_size * 0.2)
    inner_margin_tuple = parse_margin(margin_str, default_inner_margin)

    subtitle_block = TextClip(
        text=wrapped_text, font=font_path, font_size=font_size, color=f'rgb{font_color}',
        bg_color=bg_color_with_alpha, stroke_color=f'rgb{stroke_color}', stroke_width=stroke_width,
        method='label', text_align=text_align, margin=inner_margin_tuple, interline=interline
    )
    subtitle_block = subtitle_block.with_start(start_time).with_duration(end_time - start_time)
    
    y_pos = video_height - subtitle_block.h - vertical_pos_offset
    return subtitle_block.with_position((block_horizontal_align, y_pos))

class StaticSubtitlesToVideoMW:
    @classmethod
    def INPUT_TYPES(cls):
        font_list = get_font_list()
        return {
            "required": {
                "视频": ("IMAGE",), "帧率": ("FLOAT", {"forceInput": True}),
                "字幕文本": ("STRING", {"forceInput": True, "tooltip": "逐句时间戳"}),
                "字体": (font_list, {"tooltip": "字幕字体，放在节点目录 fonts 下"}), 
                "字体大小比例": ("FLOAT", {"default": 0.05, "min": 0.01, "max": 0.2, "step": 0.01}, {"tooltip": "字幕字体大小与视频宽度的比例"}),
                "字体颜色": ("STRING", {"default": "#FFFFFF", "tooltip": "字体颜色，格式为#RRGGBB"}), 
                "字体背景色": ("STRING", {"default": "#0000FF", "tooltip": "字体背景颜色，格式为#RRGGBB"}),
                "背景透明度": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1}, {"tooltip": "字幕背景透明度，0为完全透明，1为完全不透明"}),
            },
            "optional": {
                "字幕宽度比例": ("FLOAT", {"default": 0.9, "min": 0.1, "max": 1.0, "step": 0.05}, {"tooltip": "字幕宽度与视频宽度的比例"}),
                "垂直向上偏移": ("INT", {"default": 30, "min": 0, "max": 2000, "step": 5}, {"tooltip": "字幕块垂直向上偏移量"}),
                # "字幕块水平位置": (["left", "center", "right"], {"default": "center"}, {"tooltip": "字幕块水平位置"}),
                "文本行对齐方式": (["left", "center", "right"], {"default": "center"}, {"tooltip": "文本行对齐方式"}),
                "行间距": ("INT", {"default": 4, "min": 0, "max": 100, "step": 1}, {"tooltip": "字幕行间距"}),
                "描边宽度": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 20.0, "step": 0.1}, {"tooltip": "字幕字体描边宽度"}),
                "描边颜色": ("STRING", {"default": "", "tooltip": "留空则使用与字体相同的颜色, 格式为 #RRGGBB"}),
                "行内字体上边距": ("INT", {"default": 5, "min": 0, "max": 100, "step": 1}, {"tooltip": "字幕字体与背景框顶部的间距"}),
                "行内字体下边距": ("INT", {"default": 10, "min": 0, "max": 100, "step": 1}, {"tooltip": "字幕字体与背景框底部的间距"}),
                "去除标点符号": ("BOOLEAN", {"default": False, "tooltip": "是否去除所有标点符号并替换为空格"}),
            }
        }
    RETURN_TYPES = ("IMAGE",); RETURN_NAMES = ("静态字幕视频",)
    FUNCTION = "add_subtitles"; CATEGORY = "🎤MW/MW-ASR"

    def add_subtitles(self, 视频, 帧率, 字幕文本, 字体, 字体大小比例, 字体颜色, 字体背景色, 背景透明度,
                     字幕宽度比例=0.9, 垂直向上偏移=30, 字幕块水平位置="center", 文本行对齐方式="center",
                     行间距=4, 描边宽度=1.0, 描边颜色="", 行内字体上边距=5, 行内字体下边距=10, 去除标点符号=False):

        if isinstance(视频, torch.Tensor):
            video_np = 视频.cpu().numpy()
            if video_np.ndim == 5 and video_np.shape[0] == 1: video_np = video_np.squeeze(0)
            if video_np.dtype == np.float32 or video_np.dtype == np.float64:
                 video_np = (video_np * 255).astype(np.uint8)
        else: raise ValueError("输入视频格式不正确")
        
        temp_input_path = tempfile.NamedTemporaryFile(suffix='.mp4', dir=cache_dir, delete=False).name
        temp_output_path = tempfile.NamedTemporaryFile(suffix='.mp4', dir=cache_dir, delete=False).name
        clip = ImageSequenceClip(list(video_np), fps=帧率)
        clip.write_videofile(temp_input_path, codec='libx264', audio_codec='aac')

        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", 字体)
        font_color_rgb, bg_color_rgb = hex_to_rgb(字体颜色), hex_to_rgb(字体背景色)
        stroke_color_rgb = hex_to_rgb(描边颜色) if 描边颜色.strip() else font_color_rgb

        try: 
            subtitles_data = reverse_convert_to_list(字幕文本)
        except ValueError: raise ValueError("错误：字幕文本不是有效的格式。")
        
        if subtitles_data:
            lang, _ = langid.classify(字幕文本)
        else: lang = 'en'
        
        if 去除标点符号:
            subtitles_data = clean_punctuation_from_subtitles(subtitles_data, lang=lang)

        video_clip_in = VideoFileClip(temp_input_path)
        video_width, video_height = video_clip_in.size
        
        font_size_px = int(video_width * 字体大小比例)

        subtitle_settings = {
            'font_size': font_size_px, 'font_path': font_path, 'font_color': font_color_rgb,
            'bg_color': bg_color_rgb, 'bg_opacity': 背景透明度, 'line_width_ratio': 字幕宽度比例,
            'vertical_pos_offset': 垂直向上偏移, 'interline': 行间距, 'stroke_width': 描边宽度,
            'stroke_color': stroke_color_rgb, 'margin_tuple': f"5, {行内字体上边距}, 5, {行内字体下边距}", 'text_align': 文本行对齐方式,
            'block_horizontal_align': 字幕块水平位置, 'language': lang,
        }
        
        subtitle_clips = [create_static_subtitle_clip(text, start, end, video_width, video_height, **subtitle_settings) 
                          for start, end, text in subtitles_data]
        
        final_clip = CompositeVideoClip([video_clip_in] + subtitle_clips)
        final_clip.write_videofile(temp_output_path, codec='libx264', audio_codec='aac', threads=4, preset='fast')
        
        output_clip = VideoFileClip(temp_output_path)
        output_frames = [torch.from_numpy(frame).float() / 255.0 for frame in output_clip.iter_frames()]
        output_clip.close()

        return (torch.stack(output_frames),)

# ==============================================================================
#  NODE 2: DYNAMIC SUBTITLES
# ==============================================================================

def generate_dynamic_subtitles(subtitles, video_width, video_height, **kwargs):
    font_path = kwargs.get('font_path', 'msyh.ttc')
    font_size = kwargs.get('font_size', 24)
    font_color = kwargs.get('font_color', (255, 255, 255))
    bg_color = kwargs.get('bg_color', (0, 0, 0))
    bg_opacity = kwargs.get('bg_opacity', 0.5)
    stroke_color = kwargs.get('stroke_color', font_color)
    stroke_width = kwargs.get('stroke_width', 0.5)
    line_width_ratio = kwargs.get('line_width_ratio', 0.8)
    vertical_pos_offset = kwargs.get('vertical_pos_offset', 0)
    interline = kwargs.get('interline', 10)
    clearance_threshold = kwargs.get('clearance_threshold', 2.0)
    margin_str = kwargs.get('margin_tuple', '')
    language = kwargs.get('language', 'en')
    max_lines = kwargs.get('max_lines', 3)
    text_align = 'left'
    
    allowed_width = int(video_width * line_width_ratio)
    bg_color_with_alpha = bg_color + (int(bg_opacity * 255),)
    default_inner_margin = int(font_size * 0.1)
    inner_margin_tuple = parse_margin(margin_str, default_inner_margin)
    is_chinese = language != 'en'

    if not subtitles: return []
    blocks = []
    current_block = []
    
    last_word_end_time = -clearance_threshold - 1
    for i, (start, end, word) in enumerate(subtitles):
        
        if start - last_word_end_time > clearance_threshold:
            if current_block: 
                blocks.append(current_block)
            current_block = [] 
        current_block.append({'start': start, 'end': end, 'text': word})
        last_word_end_time = end
    if current_block: blocks.append(current_block)

    all_clips = []
    for block in blocks:
        
        lines = [""] 
        for i, word_data in enumerate(block):
            
            word_to_add = word_data['text'].strip()
            if not word_to_add:
                
                continue

            current_line = lines[-1]
            if is_chinese:
                
                test_line = current_line + word_to_add
            else:
                
                separator = " " if current_line else ""
                test_line = current_line + separator + word_to_add

            test_clip = TextClip(text=test_line, font=font_path, font_size=font_size, 
                                 stroke_width=stroke_width, method='label')
            
            if test_clip.w <= allowed_width:
                
                lines[-1] = test_line
            else:
                
                lines.append(word_to_add)
            visible_lines = lines[-max_lines:]

            line_clips = [TextClip(text=line, font=font_path, font_size=font_size, color=f'rgb{font_color}', 
                                   bg_color=f'rgba{bg_color_with_alpha}', stroke_color=f'rgb{stroke_color}', 
                                   stroke_width=stroke_width, method='label', 
                                   text_align=text_align, margin=inner_margin_tuple) 
                          for line in visible_lines if line.strip()]
            
            if not line_clips: continue
            total_height = sum(lc.h for lc in line_clips) + max(0, len(line_clips) - 1) * interline
            
            max_line_width = max(lc.w for lc in line_clips) if line_clips else 0
            canvas_size = (max_line_width, int(total_height))
            
            y_pos_on_canvas = 0
            positioned_clips = []
            for lc in line_clips:
                
                positioned_clip = lc.with_position((0, y_pos_on_canvas))
                positioned_clips.append(positioned_clip)
                y_pos_on_canvas += lc.h + interline
            
            moment_canvas = CompositeVideoClip(positioned_clips, size=canvas_size).with_opacity(1)
            
            start_time = word_data['start']
            
            end_time = block[i+1]['start'] if i + 1 < len(block) else block[-1]['end']
            duration = end_time - start_time
            if duration <= 0.01: continue
            y_final = video_height - moment_canvas.h - vertical_pos_offset
            final_clip_for_moment = moment_canvas.with_start(start_time).with_duration(duration).with_position(('center', y_final))
            all_clips.append(final_clip_for_moment)
            
    return all_clips

class DynamicSubtitlesToVideoMW:
    @classmethod
    def INPUT_TYPES(cls):
        font_list = get_font_list()
        return {
            "required": {
                "视频": ("IMAGE",), 
                "帧率": ("FLOAT", {"forceInput": True, "tooltip": "视频帧率"}),
                "字幕文本": ("STRING", {"forceInput": True, "tooltip": "逐词时间戳"}),
                "字体": (font_list, {"tooltip": "字幕字体, 放在节点文件夹 fonts 下"}), 
                "字体大小比例": ("FLOAT", {"default": 0.05, "min": 0.01, "max": 0.2, "step": 0.01, "tooltip": "字幕字体大小与视频宽度的比例"}),
                "字体颜色": ("STRING", {"default": "#FFFFFF", "tooltip": "字幕字体颜色, 格式为 #RRGGBB"}), 
                "字体背景色": ("STRING", {"default": "#000000", "tooltip": "字幕字体背景颜色, 格式为 #RRGGBB"}), 
                "背景透明度": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.1, "tooltip": "字幕字体背景透明度, 0为完全透明, 1为完全不透明"}),
            },
            "optional": {
                "最大行数": ("INT", {"default": 2, "min": 1, "max": 10, "step": 1, "tooltip": "屏幕上同时显示的最大字幕行数"}),
                "字幕宽度比例": ("FLOAT", {"default": 0.9, "min": 0.1, "max": 1.0, "step": 0.05, "tooltip": "字幕宽度与视频宽度的比例"}),
                "垂直向上偏移": ("INT", {"default": 50, "min": 0, "max": 2000, "step": 10, "tooltip": "字幕垂直向上偏移的像素数"}),
                "行间距": ("INT", {"default": 3, "min": 0, "max": 100, "step": 1, "tooltip": "字幕行间距的像素数"}),
                "描边宽度": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 20.0, "step": 0.1, "tooltip": "字幕字体描边宽度, 0为不描边"}),
                "描边颜色": ("STRING", {"default": "", "tooltip": "留空则使用与字体相同的颜色, 格式为 #RRGGBB"}),
                "行内字体上边距": ("INT", {"default": 5, "min": 0, "max": 50, "step": 1, "tooltip": "字幕字体与背景框顶部的间距"}),
                "行内字体下边距": ("INT", {"default": 10, "min": 0, "max": 50, "step": 1, "tooltip": "字幕字体与背景框底部的间距"}),
                "清空阈值": ("FLOAT", {"default": 2.0, "min": 0.1, "max": 10.0, "step": 0.1, "tooltip": "前后两句话之间静音超过该秒数，则清空字幕重新开始"}),
                "去除标点符号": ("BOOLEAN", {"default": False, "tooltip": "是否去除所有标点符号"}),
            }
        }
    RETURN_TYPES = ("IMAGE",); RETURN_NAMES = ("动态字幕视频",)
    FUNCTION = "add_dynamic_subtitles"; CATEGORY = "🎤MW/MW-ASR"
    
    def add_dynamic_subtitles(self, 视频, 帧率, 字幕文本, 字体, 字体大小比例, 字体颜色, 字体背景色, 背景透明度, 
                     最大行数=3, 字幕宽度比例=0.9, 垂直向上偏移=50, 行间距=10, 描边宽度=1.0, 
                     描边颜色="", 行内字体上边距=5, 行内字体下边距=5, 清空阈值=2.0, 去除标点符号=False):
        if isinstance(视频, torch.Tensor):
            video_np = 视频.cpu().numpy()
            if video_np.ndim == 4: 
                
                if video_np.shape[0] == 1 and 视频.dim() == 4:
                   video_np = np.squeeze(video_np, axis=0)
            elif video_np.ndim == 5: 
                if video_np.shape[0] == 1:
                    video_np = np.squeeze(video_np, axis=0)
                else:
                    raise ValueError("输入视频批次大小应为1")

            if video_np.dtype == np.float32 or video_np.dtype == np.float64:
                 video_np = (video_np * 255).astype(np.uint8)
        else: raise ValueError("输入视频格式不正确")
        
        temp_input_path = tempfile.NamedTemporaryFile(suffix='.mp4', dir=cache_dir, delete=False).name
        temp_output_path = tempfile.NamedTemporaryFile(suffix='.mp4', dir=cache_dir, delete=False).name

        frames_list = [frame for frame in video_np]
        clip = ImageSequenceClip(frames_list, fps=帧率)
        clip.write_videofile(temp_input_path, codec='libx264', audio=False, threads=4, preset='fast', logger=None)

        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", 字体)
        font_color_rgb, bg_color_rgb = hex_to_rgb(字体颜色), hex_to_rgb(字体背景色)
        stroke_color_rgb = hex_to_rgb(描边颜色) if 描边颜色.strip() else font_color_rgb

        try: 
            subtitles_data = reverse_convert_to_list(字幕文本)
        except ValueError: 
             raise ValueError("错误：字幕文本不是有效的格式。")
        
        if subtitles_data:
            lang, _ = langid.classify(字幕文本)
        else: 
            lang = 'en' 
        
        if 去除标点符号:
            subtitles_data = clean_punctuation_from_subtitles(subtitles_data, lang=lang)
            
        video_clip_in = VideoFileClip(temp_input_path)
        video_width, video_height = video_clip_in.size
        
        font_size_px = int(video_height * 字体大小比例)
        
        subtitle_settings = {
            'font_path': font_path, 'font_size': font_size_px, 'font_color': font_color_rgb,
            'bg_color': bg_color_rgb, 'bg_opacity': 背景透明度, 'line_width_ratio': 字幕宽度比例,
            'vertical_pos_offset': 垂直向上偏移, 'interline': 行间距, 'stroke_width': 描边宽度,
            'stroke_color': stroke_color_rgb, 'margin_tuple': f"5, {行内字体上边距}, 5, {行内字体下边距}", 'clearance_threshold': 清空阈值,
            'language': lang, 'max_lines': 最大行数,
        }

        subtitle_clips = generate_dynamic_subtitles(subtitles_data, video_width, video_height, **subtitle_settings)
        
        final_clip = CompositeVideoClip([video_clip_in] + subtitle_clips)
        final_clip.write_videofile(temp_output_path, codec='libx264', audio=False, threads=4, preset='fast', logger=None)
        
        output_clip = VideoFileClip(temp_output_path)
        output_frames = [torch.from_numpy(frame).float() / 255.0 for frame in output_clip.iter_frames()]
        output_clip.close()
        video_clip_in.close()

        return (torch.stack(output_frames),)