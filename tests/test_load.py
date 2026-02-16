"""Tests for Load処理."""

import pathlib
from typing import Final

import pandas as pd
import pytest

from python_etl.load import load
from python_etl.transform import aggregate, clean_customers, clean_sales, merge_and_enrich

# テスト用の定数
TEST_CUSTOMERS_DATA: Final[list[dict[str, object]]] = [
    {
        "customer_id": 1,
        "name": "田中太郎",
        "email": "tanaka@example.com",
        "age": 30,
        "prefecture": "東京都",
        "registered_at": "2024-01-01",
    },
    {
        "customer_id": 2,
        "name": "佐藤花子",
        "email": None,
        "age": None,
        "prefecture": "大阪府",
        "registered_at": "2024-01-02",
    },
    {
        "customer_id": 3,
        "name": "鈴木一郎",
        "email": "suzuki@example.com",
        "age": 45,
        "prefecture": "神奈川県",
        "registered_at": "2024-01-03",
    },
]

TEST_PRODUCTS_DATA: Final[list[dict[str, object]]] = [
    {"product_id": 101, "product_name": "ノートPC", "category": "電化製品", "unit_price": 100000},
    {"product_id": 102, "product_name": "キーボード", "category": "電化製品", "unit_price": 5000},
    {"product_id": 103, "product_name": "マウス", "category": "電化製品", "unit_price": 2000},
]

TEST_SALES_DATA: Final[list[dict[str, object]]] = [
    {"sale_id": 1, "customer_id": 1, "product_id": 101, "quantity": 1, "discount_rate": 0.1, "sale_date": "2024-01-01"},
    {"sale_id": 2, "customer_id": 2, "product_id": 102, "quantity": 2, "discount_rate": 0.0, "sale_date": "2024-01-02"},
    {
        "sale_id": 3,
        "customer_id": 3,
        "product_id": 103,
        "quantity": 3,
        "discount_rate": 0.05,
        "sale_date": "2024-01-03",
    },
    {
        "sale_id": 4,
        "customer_id": 999,
        "product_id": 101,
        "quantity": None,
        "discount_rate": 0.0,
        "sale_date": "2024-01-04",
    },
]


@pytest.fixture
def customers_df() -> pd.DataFrame:
    """顧客データのDataFrameを返すfixture。"""
    return pd.DataFrame(TEST_CUSTOMERS_DATA)


@pytest.fixture
def products_df() -> pd.DataFrame:
    """商品データのDataFrameを返すfixture。"""
    return pd.DataFrame(TEST_PRODUCTS_DATA)


@pytest.fixture
def sales_df() -> pd.DataFrame:
    """売上データのDataFrameを返すfixture。"""
    return pd.DataFrame(TEST_SALES_DATA)


def test_load(
    sales_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    tmp_path: pathlib.Path,
) -> None:
    """load関数がCSVファイルを正しく出力することをテスト。"""
    # 事前にクレンジングと結合
    customers = clean_customers(customers_df)
    sales = clean_sales(sales_df, customers, products_df)
    enriched = merge_and_enrich(sales, customers, products_df)
    customer_summary, category_summary, daily_sales = aggregate(enriched)

    out_dir = tmp_path / "output"
    load(enriched, customer_summary, category_summary, daily_sales, out_dir=out_dir)

    # ファイルが作成されていることを確認
    assert (out_dir / "sales_enriched.csv").exists()
    assert (out_dir / "customer_summary.csv").exists()
    assert (out_dir / "category_summary.csv").exists()
    assert (out_dir / "daily_sales.csv").exists()

    # ファイルの内容を確認
    loaded_enriched = pd.read_csv(out_dir / "sales_enriched.csv")
    assert len(loaded_enriched) == len(enriched)


def test_load_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """load関数がディレクトリ作成に失敗した場合に例外を発生させることをテスト。"""

    def mock_mkdir(*args: object, **kwargs: object) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr(pathlib.Path, "mkdir", mock_mkdir)

    # テストデータを作成
    test_df = pd.DataFrame({"col1": [1, 2, 3]})

    with pytest.raises((OSError, PermissionError)):
        load(test_df, test_df, test_df, test_df)
