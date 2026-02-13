"""Tests for ETL pipeline functions."""

import pathlib
import tempfile
from typing import Final

import pandas as pd
import pytest

from python_etl.etl import (
    aggregate,
    clean_customers,
    clean_sales,
    extract,
    load,
    merge_and_enrich,
)

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


@pytest.fixture
def temp_csv_dir(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """一時的なCSVディレクトリを作成するfixture。"""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # テストデータをCSVとして保存
    pd.DataFrame(TEST_CUSTOMERS_DATA).to_csv(raw_dir / "customers.csv", index=False)
    pd.DataFrame(TEST_PRODUCTS_DATA).to_csv(raw_dir / "products.csv", index=False)
    pd.DataFrame(TEST_SALES_DATA).to_csv(raw_dir / "sales.csv", index=False)

    out_dir = tmp_path / "processed"
    return raw_dir, out_dir


def test_extract_success(temp_csv_dir: tuple[pathlib.Path, pathlib.Path], monkeypatch: pytest.MonkeyPatch) -> None:
    """extract関数が正常にCSVファイルを読み込むことをテスト。"""
    raw_dir, _ = temp_csv_dir
    monkeypatch.setattr("python_etl.etl.RAW_DIR", raw_dir)

    customers, products, sales = extract()

    assert len(customers) == 3
    assert len(products) == 3
    assert len(sales) == 4
    assert "customer_id" in customers.columns
    assert "product_id" in products.columns
    assert "sale_id" in sales.columns


def test_extract_file_not_found(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """extract関数がファイルが存在しない場合に例外を発生させることをテスト。"""
    non_existent_dir = tmp_path / "non_existent"
    monkeypatch.setattr("python_etl.etl.RAW_DIR", non_existent_dir)

    with pytest.raises(OSError):
        extract()


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


def test_load(sales_df: pd.DataFrame, customers_df: pd.DataFrame, products_df: pd.DataFrame) -> None:
    """load関数がCSVファイルを正しく出力することをテスト。"""
    # 事前にクレンジングと結合
    customers = clean_customers(customers_df)
    sales = clean_sales(sales_df, customers, products_df)
    enriched = merge_and_enrich(sales, customers, products_df)
    customer_summary, category_summary, daily_sales = aggregate(enriched)

    # 一時ディレクトリに出力
    with tempfile.TemporaryDirectory() as tmpdir:
        import python_etl.etl

        original_out_dir = python_etl.etl.OUT_DIR
        python_etl.etl.OUT_DIR = pathlib.Path(tmpdir)

        try:
            load(enriched, customer_summary, category_summary, daily_sales)

            # ファイルが作成されていることを確認
            assert (pathlib.Path(tmpdir) / "sales_enriched.csv").exists()
            assert (pathlib.Path(tmpdir) / "customer_summary.csv").exists()
            assert (pathlib.Path(tmpdir) / "category_summary.csv").exists()
            assert (pathlib.Path(tmpdir) / "daily_sales.csv").exists()

            # ファイルの内容を確認
            loaded_enriched = pd.read_csv(pathlib.Path(tmpdir) / "sales_enriched.csv")
            assert len(loaded_enriched) == len(enriched)
        finally:
            python_etl.etl.OUT_DIR = original_out_dir


def test_load_permission_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """load関数がディレクトリ作成に失敗した場合に例外を発生させることをテスト。"""

    def mock_mkdir(*args: object, **kwargs: object) -> None:
        raise PermissionError("Permission denied")

    monkeypatch.setattr(pathlib.Path, "mkdir", mock_mkdir)

    # テストデータを作成
    test_df = pd.DataFrame({"col1": [1, 2, 3]})

    with pytest.raises((OSError, PermissionError)):
        load(test_df, test_df, test_df, test_df)
