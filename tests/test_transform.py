"""Tests for Transform処理."""

from typing import Final

import pandas as pd
import pytest

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


def test_clean_customers(customers_df: pd.DataFrame) -> None:
    """clean_customers関数が欠損値を正しく補完することをテスト。"""
    result = clean_customers(customers_df)

    # 欠損メールアドレスが補完されている
    assert result.loc[1, "email"] == "unknown@example.com"

    # 欠損年齢が中央値で補完されている（30と45の中央値は37.5 -> 38）
    assert result.loc[1, "age"] == 37

    # 登録日がdatetime型に変換されている
    assert pd.api.types.is_datetime64_any_dtype(result["registered_at"])


def test_clean_customers_with_registered_at() -> None:
    """clean_customers関数がregistered_atを正しく変換することをテスト。"""
    test_data = [
        {
            "customer_id": 1,
            "name": "田中太郎",
            "email": "tanaka@example.com",
            "age": 30,
            "prefecture": "東京都",
            "registered_at": "2024-01-01",
        }
    ]
    df = pd.DataFrame(test_data)
    result = clean_customers(df)

    assert pd.api.types.is_datetime64_any_dtype(result["registered_at"])


def test_clean_customers_missing_column() -> None:
    """clean_customers関数が必要なカラムがない場合に例外を発生させることをテスト。"""
    df = pd.DataFrame({"customer_id": [1], "name": ["田中太郎"]})

    with pytest.raises(KeyError):
        clean_customers(df)


def test_clean_sales(sales_df: pd.DataFrame, customers_df: pd.DataFrame, products_df: pd.DataFrame) -> None:
    """clean_sales関数が欠損値と参照整合性チェックを正しく行うことをテスト。"""
    result = clean_sales(sales_df, customers_df, products_df)

    # 欠損値がある行（sale_id=4）が除外されている
    assert 4 not in result["sale_id"].values

    # 存在しない顧客ID（customer_id=999）の行が除外されている
    assert 999 not in result["customer_id"].values

    # 有効な行のみが残っている
    assert len(result) == 3

    # 型が正しく変換されている
    assert result["quantity"].dtype == "int64"
    assert pd.api.types.is_datetime64_any_dtype(result["sale_date"])


def test_clean_sales_missing_column(customers_df: pd.DataFrame, products_df: pd.DataFrame) -> None:
    """clean_sales関数が必要なカラムがない場合に例外を発生させることをテスト。"""
    df = pd.DataFrame({"sale_id": [1], "customer_id": [1]})

    with pytest.raises(KeyError):
        clean_sales(df, customers_df, products_df)


def test_merge_and_enrich(sales_df: pd.DataFrame, customers_df: pd.DataFrame, products_df: pd.DataFrame) -> None:
    """merge_and_enrich関数がテーブル結合と売上金額計算を正しく行うことをテスト。"""
    # 事前にクレンジング
    customers = clean_customers(customers_df)
    sales = clean_sales(sales_df, customers, products_df)

    result = merge_and_enrich(sales, customers, products_df)

    # 結合されたカラムが存在する
    assert "name" in result.columns
    assert "prefecture" in result.columns
    assert "product_name" in result.columns
    assert "category" in result.columns
    assert "unit_price" in result.columns
    assert "total_amount" in result.columns

    # 売上金額が正しく計算されている（sale_id=1: 100000 * 1 * (1 - 0.1) = 90000）
    first_sale = result[result["sale_id"] == 1].iloc[0]
    assert first_sale["total_amount"] == 90000


def test_merge_and_enrich_missing_column(customers_df: pd.DataFrame, products_df: pd.DataFrame) -> None:
    """merge_and_enrich関数が必要なカラムがない場合に例外を発生させることをテスト。"""
    df = pd.DataFrame({"sale_id": [1]})

    with pytest.raises(KeyError):
        merge_and_enrich(df, customers_df, products_df)


def test_aggregate(sales_df: pd.DataFrame, customers_df: pd.DataFrame, products_df: pd.DataFrame) -> None:
    """aggregate関数が集計を正しく行うことをテスト。"""
    # 事前にクレンジングと結合
    customers = clean_customers(customers_df)
    sales = clean_sales(sales_df, customers, products_df)
    enriched = merge_and_enrich(sales, customers, products_df)

    customer_summary, category_summary, daily_sales = aggregate(enriched)

    # 顧客別サマリー
    assert len(customer_summary) == 3
    assert "customer_id" in customer_summary.columns
    assert "purchase_count" in customer_summary.columns
    assert "total_amount" in customer_summary.columns
    assert "avg_amount" in customer_summary.columns

    # カテゴリ別サマリー
    assert len(category_summary) == 1  # すべて「電化製品」
    assert category_summary.iloc[0]["category"] == "電化製品"

    # 日別売上
    assert len(daily_sales) == 3  # 3つの異なる日付
    assert "sale_date" in daily_sales.columns
    assert "sale_count" in daily_sales.columns
    assert "total_amount" in daily_sales.columns


def test_aggregate_missing_column(customers_df: pd.DataFrame) -> None:
    """aggregate関数が必要なカラムがない場合に例外を発生させることをテスト。"""
    df = pd.DataFrame({"customer_id": [1]})

    with pytest.raises(KeyError):
        aggregate(df)
