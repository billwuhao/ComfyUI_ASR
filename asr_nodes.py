import folder_paths
import os
import tempfile
import torchaudio
from typing import Optional
from faster_whisper import WhisperModel
import torch
import langid
import jieba
# from comfy.utils import ProgressBar
from .MW_utils.hf_download import download_model_with_snapshot
from .timestamp_alignment import (
    align_chunks_to_timestamps,
    chunk_chinese_tokens,
    is_punctuation,
    normalize_text,
)


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


def convert_to_string(lst):
    return "\n".join([f"({x[0]}, {x[1]}) {x[2]}" for x in lst])

def create_custom_sentences(words_list, sentences_list, max_len, lang="zh", sentence_words_list=None):
    full_text = "".join([s[2] for s in sentences_list])
    if not full_text: return []
    custom_sentences_list = []
    global_word_cursor = 0

    for sentence_index, (sent_start, sent_end, sent_text) in enumerate(sentences_list):
        if sentence_words_list is not None and sentence_index < len(sentence_words_list):
            sentence_words = sentence_words_list[sentence_index]
        else:
            # Backward-compatible fallback for callers that only provide the
            # flattened word list. Compare normalized characters so punctuation
            # does not consume the cursor early.
            sentence_words = []
            target_length = len(normalize_text(sent_text))
            reconstructed_length = 0
            while global_word_cursor < len(words_list) and reconstructed_length < target_length:
                word = words_list[global_word_cursor]
                sentence_words.append(word)
                reconstructed_length += len(normalize_text(word[2]))
                global_word_cursor += 1

        if lang == "zh":
            jieba_words = [w.strip() for w in jieba.lcut(sent_text) if w.strip()]
            chunks = chunk_chinese_tokens(jieba_words, max_len)
            custom_sentences_list.extend(
                align_chunks_to_timestamps(
                    chunks,
                    sentence_words,
                    sent_start,
                    sent_end,
                )
            )
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

def generate_srt(custom_sentences_list):
    srt_content = ""
    for i, sentence in enumerate(custom_sentences_list, start=1):
        start_time, end_time, text = sentence
        start_time_str = f"{int(start_time // 3600):02}:{int((start_time % 3600) // 60):02}:{int(start_time % 60):02},{int((start_time % 1) * 1000):03}"
        end_time_str = f"{int(end_time // 3600):02}:{int((end_time % 3600) // 60):02}:{int(end_time % 60):02},{int((end_time % 1) * 1000):03}"
        srt_content += f"{i}\n{start_time_str} --> {end_time_str}\n{text.strip()}\n\n"
    return srt_content

MODEL_CACHE = None
class ASRMW:
    models_list = ["k1nto/Belle-whisper-large-v3-zh-punct-ct2", "CWTchen/Belle-whisper-large-v3-zh-punct-ct2-float32", "erik-svensson-cm/whisper-large-v3-ct2"]
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

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("纯文本", "时间戳单词", "时间戳句子","SRT字幕")
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
            model_asr = os.path.join(model_path, 模型.split("/")[-1])
            allow_patterns = ["config.json", "model.bin", "tokenizer.json", "preprocessor_config.json", "vocabulary.json"]
            download_model_with_snapshot(repo_id=模型, local_dir=model_asr, allow_patterns=allow_patterns)
            print(f"Loading ASR model from: {model_asr}")
            
            if not os.path.exists(model_asr):
                raise FileNotFoundError(f"Model file not found: {model_asr}. Please check paths.")
            MODEL_CACHE = WhisperModel(model_asr, device=self.device)
            self.model_name = 模型

        segments, info = MODEL_CACHE.transcribe(audio_file, word_timestamps=True)
        words_list = []
        sentences_list = []
        sentence_words_list = []
        for segment in segments:
            sentence_words = []
            for i in segment.words:
                word = [round(i.start, 2), round(i.end, 2), i.word.strip()]
                words_list.append(word)
                sentence_words.append(word)
            sentences_list.append([round(segment.start, 2), round(segment.end, 2), segment.text.strip()])
            sentence_words_list.append(sentence_words)
        
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
                sentence_words_list=sentence_words_list,
            )
        
        if 卸载模型:
            MODEL_CACHE = None
            torch.cuda.empty_cache()

        return (纯文本, convert_to_string(words_list), convert_to_string(custom_sentences_list), generate_srt(custom_sentences_list))





    























    





    
