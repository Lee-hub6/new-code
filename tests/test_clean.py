from review_insights.clean import light_clean, tokenize_for_freq


def test_light_clean_removes_url():
    out = light_clean("Check this http://example.com now")
    assert "http://example.com" not in out
    assert "check this" in out.lower()


def test_light_clean_removes_username():
    out = light_clean("thanks @seller123 for the help")
    assert "@seller123" not in out


def test_light_clean_collapses_whitespace():
    assert light_clean("  lots   of   space  ") == "lots of space"


def test_light_clean_keeps_punctuation():
    # VADER 需要标点和大小写，轻度清洗不该删掉它们
    out = light_clean("Very good!!!")
    assert "!!!" in out


def test_tokenize_removes_stopwords():
    tokens = tokenize_for_freq("the app is really good", "en")
    assert "the" not in tokens
    assert "is" not in tokens
    assert "good" in tokens


def test_tokenize_chinese():
    tokens = tokenize_for_freq("质量很好物流快", "zh")
    # 中文走 jieba，单字被过滤
    assert all(len(t) >= 2 for t in tokens)
    assert len(tokens) > 0
