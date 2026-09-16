import re


PUNCTUATION = "＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃『』【】〖〗〘〙〚〛〜〝〞〟–—‘’‛„‟…‧﹏." \
              "!?(),;:[]{}<>\"+-=&^*%$#@/" \
              "。？！，、；：“”‘'《》〈〉「」〔〕——·~`-"


def normalize_text(text):
    """Remove characters that should not consume a subtitle text position."""
    return re.sub(r"[\s" + re.escape(PUNCTUATION) + r"]+", "", text or "")


def is_punctuation(text):
    stripped = (text or "").strip()
    return bool(stripped) and all(char in PUNCTUATION for char in stripped)


def chunk_chinese_tokens(tokens, max_len):
    """Split jieba tokens while keeping punctuation attached to nearby text."""
    max_len = max(1, int(max_len))
    chunks = []
    leading_punctuation = ""
    cursor = 0

    while cursor < len(tokens):
        core_tokens = []
        current_len = 0

        while cursor < len(tokens):
            token = (tokens[cursor] or "").strip()
            if not token:
                cursor += 1
                continue
            if is_punctuation(token):
                break

            token_len = len(normalize_text(token))
            if current_len + token_len > max_len and core_tokens:
                break

            core_tokens.append(token)
            current_len += token_len
            cursor += 1

        if not core_tokens:
            if cursor >= len(tokens):
                break
            punctuation = (tokens[cursor] or "").strip()
            if chunks:
                chunks[-1] += punctuation
            else:
                leading_punctuation += punctuation
            cursor += 1
            continue

        chunk_text = leading_punctuation + "".join(core_tokens)
        leading_punctuation = ""

        while cursor < len(tokens):
            token = (tokens[cursor] or "").strip()
            if not token:
                cursor += 1
                continue
            if not is_punctuation(token):
                break
            chunk_text += token
            cursor += 1

        chunks.append(chunk_text)

    if leading_punctuation:
        if chunks:
            chunks[-1] += leading_punctuation
        else:
            chunks.append(leading_punctuation)

    return chunks


def _fallback_alignment(chunks, start_time, end_time):
    """Distribute chunks over a segment when word timestamps are unavailable."""
    if not chunks:
        return []

    start_time = float(start_time)
    end_time = max(start_time, float(end_time))
    lengths = [len(normalize_text(chunk)) for chunk in chunks]
    total_length = sum(lengths)
    if total_length == 0:
        lengths = [1] * len(chunks)
        total_length = len(chunks)

    result = []
    consumed = 0
    duration = end_time - start_time
    for index, (chunk, length) in enumerate(zip(chunks, lengths)):
        chunk_start = start_time + duration * consumed / total_length
        consumed += length
        chunk_end = start_time + duration * consumed / total_length
        if index == len(chunks) - 1:
            chunk_end = end_time
        result.append([round(chunk_start, 3), round(chunk_end, 3), chunk])
    return result


def align_chunks_to_timestamps(chunks, timed_words, segment_start, segment_end):
    """
    Align text chunks with Whisper word timestamps by normalized character offset.

    Text and word-token character counts do not need to match. Offsets are scaled
    between the two streams, and boundaries inside a Whisper token are
    interpolated. This keeps every subtitle chunk timed without indexing past the
    available words.
    """
    chunks = [chunk for chunk in chunks if chunk]
    if not chunks:
        return []

    word_spans = []
    word_offset = 0
    for start, end, text in timed_words or []:
        normalized_length = len(normalize_text(text))
        if normalized_length == 0:
            continue
        start = float(start)
        end = max(start, float(end))
        word_spans.append((word_offset, word_offset + normalized_length, start, end))
        word_offset += normalized_length

    chunk_lengths = [len(normalize_text(chunk)) for chunk in chunks]
    source_length = sum(chunk_lengths)
    if not word_spans or source_length == 0 or word_offset == 0:
        return _fallback_alignment(chunks, segment_start, segment_end)

    def time_at(source_offset, boundary):
        target_offset = source_offset * word_offset / source_length

        if target_offset <= 0:
            return word_spans[0][2]
        if target_offset >= word_offset:
            return word_spans[-1][3]

        for index, (span_start, span_end, time_start, time_end) in enumerate(word_spans):
            if target_offset < span_end:
                fraction = (target_offset - span_start) / (span_end - span_start)
                return time_start + (time_end - time_start) * fraction
            if target_offset == span_end:
                if boundary == "start" and index + 1 < len(word_spans):
                    return word_spans[index + 1][2]
                return time_end

        return word_spans[-1][3]

    result = []
    consumed = 0
    for index, (chunk, length) in enumerate(zip(chunks, chunk_lengths)):
        chunk_start = time_at(consumed, "start")
        consumed += length
        chunk_end = time_at(consumed, "end")

        if result:
            chunk_start = max(chunk_start, result[-1][1])
        chunk_end = max(chunk_start, chunk_end)
        if index == len(chunks) - 1:
            chunk_end = max(chunk_end, word_spans[-1][3])

        result.append([round(chunk_start, 3), round(chunk_end, 3), chunk])

    return result
