"""Tests for ETLパイプライン統合テスト."""

import importlib
import pathlib
from typing import Final

import pandas as pd
import pytest

from python_etl.etl import main

# モジュール自体をインポート
extract_module = importlib.import_module("python_etl.extract")
load_module = importlib.import_module("python_etl.load")

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
]


@pytest.fixture
def temp_etl_dirs(tmp_path: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
    """一時的なETL用ディレクトリを作成するfixture。"""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # テストデータをCSVとして保存
    pd.DataFrame(TEST_CUSTOMERS_DATA).to_csv(raw_dir / "customers.csv", index=False)
    pd.DataFrame(TEST_PRODUCTS_DATA).to_csv(raw_dir / "products.csv", index=False)
    pd.DataFrame(TEST_SALES_DATA).to_csv(raw_dir / "sales.csv", index=False)

    out_dir = tmp_path / "processed"
    return raw_dir, out_dir


def test_main_integration(temp_etl_dirs: tuple[pathlib.Path, pathlib.Path], monkeypatch: pytest.MonkeyPatch) -> None:
    """main関数が正常にETLパイプラインを実行することをテスト。"""
    raw_dir, out_dir = temp_etl_dirs

    # RAW_DIRとOUT_DIRをモック
    monkeypatch.setattr(extract_module, "RAW_DIR", raw_dir)
    monkeypatch.setattr(load_module, "OUT_DIR", out_dir)

    # ETLパイプラインを実行
    main()

    # 出力ファイルが作成されていることを確認
    assert (out_dir / "sales_enriched.csv").exists()
    assert (out_dir / "customer_summary.csv").exists()
    assert (out_dir / "category_summary.csv").exists()
    assert (out_dir / "daily_sales.csv").exists()

    # 出力ファイルの内容を確認
    enriched = pd.read_csv(out_dir / "sales_enriched.csv")
    assert len(enriched) == 3  # 有効な売上データは3件

    customer_summary = pd.read_csv(out_dir / "customer_summary.csv")
    assert len(customer_summary) == 3  # 3人の顧客
