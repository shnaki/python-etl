"""Tests for Extract処理."""

import importlib
import pathlib
from typing import Final

import pandas as pd
import pytest

# モジュール自体をインポート
extract_module = importlib.import_module("python_etl.extract")

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
def temp_csv_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """一時的なCSVディレクトリを作成するfixture。"""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # テストデータをCSVとして保存
    pd.DataFrame(TEST_CUSTOMERS_DATA).to_csv(raw_dir / "customers.csv", index=False)
    pd.DataFrame(TEST_PRODUCTS_DATA).to_csv(raw_dir / "products.csv", index=False)
    pd.DataFrame(TEST_SALES_DATA).to_csv(raw_dir / "sales.csv", index=False)

    return raw_dir


def test_extract_success(temp_csv_dir: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """extract関数が正常にCSVファイルを読み込むことをテスト。"""
    monkeypatch.setattr(extract_module, "RAW_DIR", temp_csv_dir)

    customers, products, sales = extract_module.extract()

    assert len(customers) == 3
    assert len(products) == 3
    assert len(sales) == 4
    assert "customer_id" in customers.columns
    assert "product_id" in products.columns
    assert "sale_id" in sales.columns


def test_extract_file_not_found(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """extract関数がファイルが存在しない場合に例外を発生させることをテスト。"""
    non_existent_dir = tmp_path / "non_existent"
    monkeypatch.setattr(extract_module, "RAW_DIR", non_existent_dir)

    with pytest.raises(OSError):
        extract_module.extract()
