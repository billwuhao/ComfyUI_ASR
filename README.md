ComfyUI_ASR 是一套用于语音识别和字幕处理的ComfyUI自定义节点集合，包含语音识别、字幕生成和颜色选择等功能。

很早之前我写过一个类似添加字幕节点，但问题很多。这个节点进行了重要优化和更新，并将语音自动识别节点也放到一起，方便一键添加字幕：
- 中英文语音识别基本无误（需要更多语言支持请联系我）；
- 支持静态和动态字幕，静态字幕每句话完整显示，动态字幕按字词依次显示；
- 字幕块始终水平居中，块内可选（左中右）对齐；
- **字体大小**和**字幕块宽度**自适应视频分辨率，无论512x512还是2048x2048，都完美显示，并且可调节大小和宽度；
- 字幕默认最底部，可向上调节；
- 可添加字体背景及背景色，可调节透明度；
- 可添加字体描边及描边颜色，可调节宽度（描边拉到11左右会有棉花糖效果）；
- 可选是否去除标点符号，去掉标点符号后会更美观；
- 全中文参数，无需汉化。

https://github.com/user-attachments/assets/3d445437-4be7-46c9-86a4-af6720ad6969

https://github.com/user-attachments/assets/b7f7489c-a508-49b9-924a-62ed3e104885

https://github.com/user-attachments/assets/0831e13f-27ae-493c-a3bf-9dfd23f57838

https://github.com/user-attachments/assets/045971df-2668-4044-96ad-30a2d9d03171

## 📣 更新

[2025-11-02]⚒️: v1.0.1。修复描边宽度参数非整数问题。

[2025-11-01]⚒️: 发布 v1.0.0。

## 语音识别节点

### ASRMW 节点
该节点提供语音识别功能，可将音频转换为文本和时间戳信息。

#### 参数说明：
- **模型**: 选择ASR模型，中文推荐使用带zh标记的模型。可选值: 
  - Belle-whisper-large-v3-zh-punct-ct2, 
  - Belle-whisper-large-v3-zh-punct-ct2-float32, 
  - faster-whisper-large-v3-turbo-ct2
- **音频**: 输入音频文件
- **每句最大长度**: 每句话的最大长度，中文按字数计算，英文按字母数计算
- **卸载模型**: 运行后是否卸载模型以释放显存
- **seed**: 随机种子

#### 输出：
- **纯文本**: 识别出的纯文本内容
- **时间戳单词**: 带时间戳的单词表
- **时间戳句子**: 带时间戳的句子表

## 字幕添加节点

### StaticSubtitlesToVideoMW 节点
该节点用于为视频添加静态字幕，每句话完整显示。

#### 参数说明：
- **视频**: 输入视频
- **帧率**: 视频帧率
- **字幕文本**: 逐句时间戳文本
- **字体**: 字幕字体，需放在节点目录fonts下
- **字体大小比例**: 字幕字体大小与视频宽度的比例
- **字体颜色**: 字体颜色，格式为#RRGGBB
- **字体背景色**: 字体背景颜色，格式为#RRGGBB
- **背景透明度**: 字幕背景透明度，0为完全透明，1为完全不透明

可选参数：
- **字幕宽度比例**: 字幕宽度与视频宽度的比例
- **垂直向上偏移**: 字幕块垂直向上偏移量
- **文本行对齐方式**: 文本行对齐方式 (left, center, right)
- **行间距**: 字幕行间距
- **描边宽度**: 字幕字体描边宽度
- **描边颜色**: 描边颜色，留空则使用与字体相同的颜色
- **行内字体上边距**: 字幕字体与背景框顶部的间距
- **行内字体下边距**: 字幕字体与背景框底部的间距
- **去除标点符号**: 是否去除所有标点符号并替换为空格

#### 输出：
- **静态字幕视频**: 添加了静态字幕的视频

### DynamicSubtitlesToVideoMW 节点
该节点用于为视频添加动态字幕，逐词显示，实现打字机效果。

#### 参数说明：
- **视频**: 输入视频
- **帧率**: 视频帧率
- **字幕文本**: 逐词时间戳文本
- **字体**: 字幕字体，需放在节点目录fonts下
- **字体大小比例**: 字幕字体大小与视频宽度的比例
- **字体颜色**: 字体颜色，格式为#RRGGBB
- **字体背景色**: 字体背景颜色，格式为#RRGGBB
- **背景透明度**: 字幕背景透明度，0为完全透明，1为完全不透明

可选参数：
- **最大行数**: 屏幕上同时显示的最大字幕行数
- **字幕宽度比例**: 字幕宽度与视频宽度的比例
- **垂直向上偏移**: 字幕垂直向上偏移的像素数
- **行间距**: 字幕行间距的像素数
- **描边宽度**: 字幕字体描边宽度，0为不描边
- **描边颜色**: 描边颜色，留空则使用与字体相同的颜色
- **行内字体上边距**: 字幕字体与背景框顶部的间距
- **行内字体下边距**: 字幕字体与背景框底部的间距
- **清空阈值**: 前后两句话之间静音超过该秒数，则清空字幕重新开始
- **去除标点符号**: 是否去除所有标点符号

#### 输出：
- **动态字幕视频**: 添加了动态字幕的视频

## 颜色选择器节点

### ColorPickerMW 节点
该节点提供颜色选择功能，可用于设置字幕颜色。

#### 参数说明：
- **color**: 颜色选择器，默认为红色 (#f30e0eff)

#### 输出：
- **#RRGGBB**: 选择的颜色值，格式为十六进制颜色代码

## 使用流程示例

1. 使用ASRMW节点将音频转换为文本和时间戳
2. 使用ColorPickerMW节点选择字幕颜色
3. 根据需要选择StaticSubtitlesToVideoMW或DynamicSubtitlesToVideoMW节点为视频添加字幕
4. 调整字幕参数以获得最佳显示效果

## 注意事项

- 字体文件需放置在节点目录下的fonts文件夹中
- 动态字幕需要使用逐词时间戳，静态字幕需要使用逐句时间戳
- 中文字幕会自动使用jieba分词进行处理，以获得更好的显示效果
        
## 安装

```
cd ComfyUI/custom_nodes
git clone https://github.com/billwuhao/ComfyUI_ASR.git
cd ComfyUI_ASR
pip install -r requirements.txt

# python_embeded
./python_embeded/python.exe -m pip install -r requirements.txt
```

## 模型下载

选择需要的模型（可任选其一，中文请选 “zh” 版本），下载放到 `ComfyUI/models/TTS` 目录下:

- [Belle-whisper-large-v3-zh-punct-ct2](https://hf-mirror.com/k1nto/Belle-whisper-large-v3-zh-punct-ct2)

```
   .gitattributes
    config.json
    model.bin
    preprocessor_config.json
    README.md
    tokenizer.json
    vocabulary.json
```

- [Belle-whisper-large-v3-zh-punct-ct2-float32](https://huggingface.co/CWTchen/Belle-whisper-large-v3-zh-punct-ct2-float32)
- [whisper-large-v3-ct2](https://huggingface.co/erik-svensson-cm/whisper-large-v3-ct2)

## 鸣谢


[faster-whisper](https://github.com/SYSTRAN/faster-whisper)
