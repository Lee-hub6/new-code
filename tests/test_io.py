import pandas as pd

from review_insights.io import load_reviews


def test_load_reviews_auto_detect_columns(tmp_path):
    p = tmp_path / "reviews.csv"
    pd.DataFrame({
        "content": ["nice app", "bad product", ""],
        "score": [5, 1, 3],
        "at": ["2025-01-01", "2025-01-02", "2025-01-03"],
    }).to_csv(p, index=False)

    df = load_reviews(str(p))
    # 空评论应被剔除
    assert len(df) == 2
    assert list(df.columns) == ["text", "rating", "date"]


def test_load_reviews_manual_column(tmp_path):
    p = tmp_path / "r.csv"
    pd.DataFrame({"评论": ["很好", "很差"], "评分": [5, 1]}).to_csv(p, index=False)

    df = load_reviews(str(p), text_col="评论", rating_col="评分")
    assert len(df) == 2
    assert df["rating"].tolist() == [5, 1]
