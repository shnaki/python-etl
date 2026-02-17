"""Tests for ETLパイプライン統合テスト."""

from pathlib import Path
from typing import Final

import pandas as pd
import pytest

from python_etl.etl import main, parse_args

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
def temp_etl_dirs(tmp_path: Path) -> tuple[Path, Path]:
    """一時的なETL用ディレクトリを作成するfixture。"""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    # テストデータをCSVとして保存
    pd.DataFrame(TEST_CUSTOMERS_DATA).to_csv(raw_dir / "customers.csv", index=False)
    pd.DataFrame(TEST_PRODUCTS_DATA).to_csv(raw_dir / "products.csv", index=False)
    pd.DataFrame(TEST_SALES_DATA).to_csv(raw_dir / "sales.csv", index=False)

    out_dir = tmp_path / "processed"
    return raw_dir, out_dir


def test_main_integration(temp_etl_dirs: tuple[Path, Path]) -> None:
    """main関数が正常にETLパイプラインを実行することをテスト。"""
    raw_dir, out_dir = temp_etl_dirs

    # CLI引数でディレクトリを指定してETLパイプラインを実行
    main(["--input-dir", str(raw_dir), "--output-dir", str(out_dir)])

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


def test_parse_args_defaults() -> None:
    """引数なしでparse_argsを呼んだ場合、両方Noneになることをテスト。"""
    parsed = parse_args([])

    assert parsed.input_dir is None
    assert parsed.output_dir is None


def test_parse_args_with_both_dirs() -> None:
    """--input-dirと--output-dirを両方指定した場合のテスト。"""
    parsed = parse_args(["--input-dir", "/tmp/input", "--output-dir", "/tmp/output"])

    assert parsed.input_dir == Path("/tmp/input")
    assert parsed.output_dir == Path("/tmp/output")


def test_main_with_nonexistent_input_dir(tmp_path: Path) -> None:
    """存在しない入力ディレクトリを指定した場合にOSErrorが発生することをテスト。"""
    non_existent = tmp_path / "does_not_exist"

    with pytest.raises(OSError):
        main(["--input-dir", str(non_existent)])
