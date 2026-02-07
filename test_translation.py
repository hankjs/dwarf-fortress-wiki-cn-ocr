"""
测试翻译功能
"""

from ocr_tool import load_translation_map, translate_content_by_vocab


def test_translation():
    # 加载翻译映射表
    trans_map = load_translation_map()
    vocab_map = trans_map.get("vocabulary_map", {})

    print(f"词汇映射表大小: {len(vocab_map)}")
    print(f"词条映射表大小: {len(trans_map.get('title_map', {}))}")

    # 测试翻译
    test_text = """
    The dwarf is mining iron ore in the fortress.
    He uses a pick to dig through the stone wall.
    The military squad is training in the barracks.
    """

    print("\n--- 原始文本 ---")
    print(test_text)

    translated = translate_content_by_vocab(test_text, vocab_map)

    print("\n--- 翻译后文本 ---")
    print(translated)

    # 测试一些特定词汇
    print("\n--- 测试特定词汇映射 ---")
    test_words = ["dwarf", "fortress", "iron", "mining", "military", "training"]
    for word in test_words:
        if word in vocab_map:
            print(f"  {word} -> {vocab_map[word]}")
        else:
            print(f"  {word} -> (未找到)")


if __name__ == "__main__":
    test_translation()
