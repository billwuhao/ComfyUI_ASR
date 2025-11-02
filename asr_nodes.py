import folder_paths
import os
import tempfile
import torchaudio
from typing import Optional
from faster_whisper import WhisperModel
import torch
import langid
import jieba
import re
# from comfy.utils import ProgressBar


models_dir = folder_paths.models_dir
model_path = os.path.join(models_dir, "TTS")
cache_dir = folder_paths.get_temp_directory()

def cache_audio_tensor(
    cache_dir,
    audio_tensor,
    sample_rate: int,
    filename_prefix: str = "cached_audio_",
    audio_format: Optional[str] = ".wav"
) -> str:
    try:
        with tempfile.NamedTemporaryFile(
            prefix=filename_prefix,
            suffix=audio_format,
            dir=cache_dir,
            delete=False 
        ) as tmp_file:
            temp_filepath = tmp_file.name
        
        torchaudio.save(temp_filepath, audio_tensor, sample_rate)

        return temp_filepath
    except Exception as e:
        raise Exception(f"Error caching audio tensor: {e}")


PUNCTUATION = "＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃『』【】〖〗〘〙〚〛〜〝〞〟–—‘’‛„‟…‧﹏." \
              "!?(),;:[]{}<>\"+-=&^*%$#@/" \
              "。？！，、；：“”‘'《》〈〉「」〔〕——·~`-"

def convert_to_string(lst):
    return "\n".join([f"({x[0]}, {x[1]}) {x[2]}" for x in lst])

def is_punctuation(text):
    return all(char in PUNCTUATION for char in text.strip())

def create_custom_sentences(words_list, sentences_list, max_len, lang="zh"):
    full_text = "".join([s[2] for s in sentences_list])
    if not full_text: return []
    custom_sentences_list = []
    global_word_cursor = 0

    for sent_start, sent_end, sent_text in sentences_list:
        sentence_words = []
        norm_target_text = re.sub(r'[\s' + re.escape(PUNCTUATION) + r']+', '', sent_text)
        reconstructed_text = ""
        temp_cursor = global_word_cursor
        while temp_cursor < len(words_list) and len(reconstructed_text) < len(norm_target_text):
            word_content = words_list[temp_cursor][2]
            sentence_words.append(words_list[temp_cursor])
            reconstructed_text += re.sub(r'[\s' + re.escape(PUNCTUATION) + r']+', '', word_content)
            temp_cursor += 1
        global_word_cursor = temp_cursor
        if not sentence_words: continue

        if lang == "zh":
            local_word_cursor = 0
            jieba_words = [w.strip() for w in jieba.lcut(sent_text) if w.strip()]
            jieba_cursor = 0
            
            while jieba_cursor < len(jieba_words):
                
                core_words = []
                current_len = 0
                while jieba_cursor < len(jieba_words):
                    token = jieba_words[jieba_cursor]
                    if is_punctuation(token):
                        break 
                    if current_len + len(token) > max_len and core_words:
                        break
                    core_words.append(token)
                    current_len += len(token)
                    jieba_cursor += 1
                
                if not core_words:
                    if jieba_cursor < len(jieba_words) and is_punctuation(jieba_words[jieba_cursor]):
                        if custom_sentences_list:
                            custom_sentences_list[-1][2] += jieba_words[jieba_cursor]
                        jieba_cursor += 1
                    continue
                
                chunk_text = "".join(core_words)
                chunk_len = len(chunk_text)
                
                chars_consumed = 0
                start_idx = local_word_cursor
                end_idx = local_word_cursor
                for i in range(start_idx, len(sentence_words)):
                    chars_consumed += len(sentence_words[i][2])
                    end_idx = i
                    if chars_consumed >= chunk_len: break
                
                start_time, end_time = -1, -1
                if start_idx <= end_idx:
                    start_time = sentence_words[start_idx][0]
                    end_time = sentence_words[end_idx][1]
                    local_word_cursor = end_idx + 1
                
                while jieba_cursor < len(jieba_words) and is_punctuation(jieba_words[jieba_cursor]):
                    chunk_text += jieba_words[jieba_cursor]
                    jieba_cursor += 1 
                
                if start_time != -1:
                    custom_sentences_list.append([start_time, end_time, chunk_text])
        else: 
            timed_tokens = [[s, e, w.strip()] for s, e, w in sentence_words]
            if not timed_tokens: continue
            current_chunk_tokens = []
            for token_data in timed_tokens:
                token_text = token_data[2]
                if not token_text: continue
                if not current_chunk_tokens and is_punctuation(token_text) and custom_sentences_list:
                    last_item = custom_sentences_list[-1]
                    last_item[1] = token_data[1]
                    last_item[2] += (" " + token_text)
                    continue
                if len(" ".join(t[2] for t in current_chunk_tokens)) + len(token_text) + 1 > max_len and current_chunk_tokens:
                    chunk_text = " ".join(t[2] for t in current_chunk_tokens)
                    custom_sentences_list.append([current_chunk_tokens[0][0], current_chunk_tokens[-1][1], chunk_text])
                    current_chunk_tokens = [token_data]
                else:
                    current_chunk_tokens.append(token_data)
            if current_chunk_tokens:
                chunk_text = " ".join(t[2] for t in current_chunk_tokens)
                custom_sentences_list.append([current_chunk_tokens[0][0], current_chunk_tokens[-1][1], chunk_text])

    return custom_sentences_list

MODEL_CACHE = None
class ASRMW:
    models_list = ["Belle-whisper-large-v3-zh-punct-ct2", "Belle-whisper-large-v3-zh-punct-ct2-float32", "faster-whisper-large-v3-turbo-ct2"]
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "模型": (s.models_list, {"default": s.models_list[0], "tooltip": "选择ASR模型, 中文用 zh 模型"}),
                "音频": ("AUDIO", {"tooltip": "输入音频文件"}),
                "每句最大长度": ("INT", {"default": 20, "min": 1, "max": 1000, "tooltip": "中文按字数计算，英文按字母数计算"}),
                "卸载模型": ("BOOLEAN", {"default": True, "tooltip": "运行后卸载模型以释放显存"}),  
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "step": 1, "tooltip": "随机种子"}),
            },
            "optional": {},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING",)
    RETURN_NAMES = ("纯文本", "时间戳单词", "时间戳句子",)
    FUNCTION = "run_inference"
    CATEGORY = "🎤MW/MW-ASR"

    def run_inference(
        self,
        模型,
        音频,
        每句最大长度=20,
        卸载模型=True,
        seed=0,
    ):
        if seed != 0:
            torch.manual_seed(seed) 
            torch.cuda.manual_seed_all(seed)

        audio_file = cache_audio_tensor(
            cache_dir,
            音频["waveform"].squeeze(0),
            音频["sample_rate"],
        )

        global MODEL_CACHE
        if MODEL_CACHE is None or self.model_name != 模型:
            model_asr = os.path.join(model_path, 模型)
            print(f"Loading ASR model from: {model_asr}")
            if not os.path.exists(model_asr):
                raise FileNotFoundError(f"Model file not found: {model_asr}. Please check paths.")
            MODEL_CACHE = WhisperModel(model_asr, device=self.device)
            self.model_name = 模型

        segments, info = MODEL_CACHE.transcribe(audio_file, word_timestamps=True)
        words_list = []
        sentences_list = []
        for segment in segments:
            for i in segment.words:
                words_list.append([round(i.start, 2), round(i.end, 2), i.word.strip()])
            sentences_list.append([round(segment.start, 2), round(segment.end, 2), segment.text.strip()])
        
        texts = " ".join([i[2] for i in sentences_list])
        lang, _ = langid.classify(texts)

        if lang == "zh":
            纯文本 = "".join([i[2] for i in sentences_list])
        else:
            纯文本 = texts

        custom_sentences_list = []
        custom_sentences_list = create_custom_sentences(
                words_list,
                sentences_list,
                max_len=每句最大长度,
                lang=lang,
            )
        
        if 卸载模型:
            MODEL_CACHE = None
            torch.cuda.empty_cache()

        return (纯文本, convert_to_string(words_list), convert_to_string(custom_sentences_list))





    























    





    

