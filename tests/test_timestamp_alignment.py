import unittest

from timestamp_alignment import (
    align_chunks_to_timestamps,
    chunk_chinese_tokens,
)


class TimestampAlignmentTests(unittest.TestCase):
    def test_punctuation_is_attached_to_previous_chunk(self):
        tokens = ["你好", "，", "世界", "！"]
        self.assertEqual(
            chunk_chinese_tokens(tokens, max_len=10),
            ["你好，", "世界！"],
        )

    def test_more_chunks_than_words_does_not_overrun_word_list(self):
        chunks = ["一二", "三四", "五六"]
        words = [[0.0, 3.0, "一二三四五六"]]

        result = align_chunks_to_timestamps(chunks, words, 0.0, 3.0)

        self.assertEqual([item[2] for item in result], chunks)
        self.assertEqual([(item[0], item[1]) for item in result], [
            (0.0, 1.0),
            (1.0, 2.0),
            (2.0, 3.0),
        ])

    def test_punctuation_does_not_consume_timestamp_characters(self):
        chunks = ["你好，", "世界。"]
        words = [
            [0.0, 1.0, "你好，"],
            [1.2, 2.0, "世界。"],
        ]

        result = align_chunks_to_timestamps(chunks, words, 0.0, 2.0)

        self.assertEqual(result, [
            [0.0, 1.0, "你好，"],
            [1.2, 2.0, "世界。"],
        ])

    def test_character_count_mismatch_still_keeps_every_chunk(self):
        chunks = ["今天我们", "测试字幕", "对齐逻辑"]
        words = [
            [5.0, 6.0, "今天我们测试"],
            [6.1, 7.0, "字幕对齐"],
        ]

        result = align_chunks_to_timestamps(chunks, words, 5.0, 7.2)

        self.assertEqual(len(result), 3)
        self.assertEqual("".join(item[2] for item in result), "".join(chunks))
        self.assertTrue(all(start <= end for start, end, _ in result))
        self.assertTrue(all(result[index][1] <= result[index + 1][0]
                            for index in range(len(result) - 1)))

    def test_missing_word_timestamps_falls_back_to_segment_time(self):
        result = align_chunks_to_timestamps(
            ["甲乙", "丙丁"],
            [],
            10.0,
            14.0,
        )

        self.assertEqual(result, [
            [10.0, 12.0, "甲乙"],
            [12.0, 14.0, "丙丁"],
        ])


if __name__ == "__main__":
    unittest.main()
