"""
Python + Pandas ETL サンプルプロジェクト

処理フロー:
  1. Extract  - data/raw/ から CSV ファイルを読み込む
  2. Transform - データのクレンジング・結合・集計を行う
  3. Load     - 加工結果を data/processed/ へ CSV 出力する
"""

import logging
import pathlib
from typing import Final

import pandas as pd

# ロガーの設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger: Final[logging.Logger] = logging.getLogger(__name__)

# ディレクトリパスの設定
BASE_DIR: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parent.parent.parent
RAW_DIR: Final[pathlib.Path] = BASE_DIR / "data" / "raw"
OUT_DIR: Final[pathlib.Path] = BASE_DIR / "data" / "processed"


# ========== Extract ==========
def extract() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    CSV ファイルを読み込む。

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: 顧客、商品、売上のDataFrameのタプル

    Raises:
        OSError: ファイルの読み込みに失敗した場合
        pd.errors.EmptyDataError: CSVファイルが空の場合
        pd.errors.ParserError: CSVファイルのパースに失敗した場合
    """
    try:
        customers = pd.read_csv(RAW_DIR / "customers.csv")
        products = pd.read_csv(RAW_DIR / "products.csv")
        sales = pd.read_csv(RAW_DIR / "sales.csv")
        logger.info(f"[Extract] customers: {len(customers)}件, products: {len(products)}件, sales: {len(sales)}件")
        return customers, products, sales
    except (OSError, PermissionError):
        logger.exception("CSVファイルの読み込みに失敗しました")
        raise
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        logger.exception("CSVファイルのパースに失敗しました")
        raise


# ========== Transform ==========
def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    顧客データのクレンジング。

    Args:
        df: 顧客データのDataFrame

    Returns:
        pd.DataFrame: クレンジング済みの顧客DataFrame

    Raises:
        KeyError: 必要なカラムが存在しない場合
        ValueError: データ型の変換に失敗した場合
    """
    try:
        # 欠損メールアドレスを 'unknown@example.com' で補完
        df["email"] = df["email"].fillna("unknown@example.com")
        # 欠損年齢を中央値で補完
        median_age = df["age"].median()
        if pd.notna(median_age):
            df["age"] = df["age"].fillna(median_age)
        df["age"] = df["age"].astype(int)
        # 登録日を datetime 型に変換（存在する場合のみ）
        if "registered_at" in df.columns:
            df["registered_at"] = pd.to_datetime(df["registered_at"])
        logger.info("[Transform] 顧客データクレンジング完了 (欠損補完済み)")
        return df
    except KeyError:
        logger.exception("必要なカラムが存在しません")
        raise
    except (ValueError, TypeError):
        logger.exception("データ型の変換に失敗しました")
        raise


def clean_sales(df: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """
    売上データのクレンジング。

    Args:
        df: 売上データのDataFrame
        customers: 顧客データのDataFrame
        products: 商品データのDataFrame

    Returns:
        pd.DataFrame: クレンジング済みの売上DataFrame

    Raises:
        KeyError: 必要なカラムが存在しない場合
        ValueError: データ型の変換に失敗した場合
    """
    try:
        before = len(df)

        # 欠損値がある行を除外
        df = df.dropna(subset=["quantity", "sale_date", "discount_rate"])
        dropped_na = before - len(df)

        # 存在しない顧客ID・商品IDの行を除外 (参照整合性チェック)
        valid_customers = set(customers["customer_id"])
        valid_products = set(products["product_id"])
        df = df[df["customer_id"].isin(valid_customers) & df["product_id"].isin(valid_products)]
        dropped_ref = before - dropped_na - len(df)

        # 型変換
        df["quantity"] = df["quantity"].astype(int)
        df["sale_date"] = pd.to_datetime(df["sale_date"])

        logger.info(f"[Transform] 売上データクレンジング完了 (欠損除外: {dropped_na}件, 参照不正除外: {dropped_ref}件)")
        return df
    except KeyError:
        logger.exception("必要なカラムが存在しません")
        raise
    except (ValueError, TypeError):
        logger.exception("データ型の変換に失敗しました")
        raise


def merge_and_enrich(sales: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """
    3つのテーブルを結合し、売上金額を算出する。

    Args:
        sales: 売上データのDataFrame
        customers: 顧客データのDataFrame
        products: 商品データのDataFrame

    Returns:
        pd.DataFrame: 結合・エンリッチされた売上DataFrame

    Raises:
        KeyError: 必要なカラムが存在しない場合
        ValueError: 売上金額の計算に失敗した場合
    """
    try:
        df = sales.merge(customers[["customer_id", "name", "prefecture"]], on="customer_id", how="left").merge(
            products[["product_id", "product_name", "category", "unit_price"]], on="product_id", how="left"
        )
        # 売上金額 = 単価 × 数量 × (1 - 割引率)
        df["total_amount"] = (df["unit_price"] * df["quantity"] * (1 - df["discount_rate"])).round(0).astype(int)
        logger.info(f"[Transform] テーブル結合・売上金額算出完了 ({len(df)}件)")
        return df
    except KeyError:
        logger.exception("必要なカラムが存在しません")
        raise
    except (ValueError, TypeError):
        logger.exception("売上金額の計算に失敗しました")
        raise


def aggregate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    集計レポートを生成する。

    Args:
        df: エンリッチされた売上データのDataFrame

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: 顧客別サマリー、カテゴリ別サマリー、日別売上のタプル

    Raises:
        KeyError: 必要なカラムが存在しない場合
        ValueError: 集計処理に失敗した場合
    """
    try:
        # 1. 顧客別 売上サマリー
        customer_summary = (
            df.groupby(["customer_id", "name"])
            .agg(
                purchase_count=("sale_id", "count"),
                total_amount=("total_amount", "sum"),
                avg_amount=("total_amount", "mean"),
            )
            .round(0)
            .astype({"avg_amount": int})
            .reset_index()
            .sort_values("total_amount", ascending=False)
        )

        # 2. 商品カテゴリ別 売上サマリー
        category_summary = (
            df.groupby("category")
            .agg(
                sale_count=("sale_id", "count"),
                total_quantity=("quantity", "sum"),
                total_amount=("total_amount", "sum"),
            )
            .reset_index()
            .sort_values("total_amount", ascending=False)
        )

        # 3. 日別 売上推移
        daily_sales = (
            df.groupby("sale_date")
            .agg(
                sale_count=("sale_id", "count"),
                total_amount=("total_amount", "sum"),
            )
            .reset_index()
            .sort_values("sale_date")
        )

        logger.info(
            f"[Transform] 集計完了 (顧客別: {len(customer_summary)}件, "
            f"カテゴリ別: {len(category_summary)}件, 日別: {len(daily_sales)}件)"
        )
        return customer_summary, category_summary, daily_sales
    except KeyError:
        logger.exception("必要なカラムが存在しません")
        raise
    except (ValueError, TypeError):
        logger.exception("集計処理に失敗しました")
        raise


# ========== Load ==========
def load(
    enriched: pd.DataFrame,
    customer_summary: pd.DataFrame,
    category_summary: pd.DataFrame,
    daily_sales: pd.DataFrame,
) -> None:
    """
    加工結果を CSV に出力する。

    Args:
        enriched: エンリッチされた売上DataFrame
        customer_summary: 顧客別サマリーDataFrame
        category_summary: カテゴリ別サマリーDataFrame
        daily_sales: 日別売上DataFrame

    Raises:
        OSError: ディレクトリの作成やファイルの書き込みに失敗した場合
        PermissionError: ファイルへのアクセス権限がない場合
    """
    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        files: dict[str, pd.DataFrame] = {
            "sales_enriched.csv": enriched,
            "customer_summary.csv": customer_summary,
            "category_summary.csv": category_summary,
            "daily_sales.csv": daily_sales,
        }
        for filename, df in files.items():
            path = OUT_DIR / filename
            df.to_csv(path, index=False, encoding="utf-8-sig")
            logger.info(f"[Load] {path} ({len(df)}件)")
    except (OSError, PermissionError):
        logger.exception("ファイルの書き込みに失敗しました")
        raise


# ========== Main ==========
def main() -> None:
    """ETLパイプラインのメインエントリポイント。"""
    try:
        logger.info("=" * 50)
        logger.info("ETL パイプライン開始")
        logger.info("=" * 50)

        # Extract
        customers, products, sales = extract()

        # Transform
        customers = clean_customers(customers)
        sales = clean_sales(sales, customers, products)
        enriched = merge_and_enrich(sales, customers, products)
        customer_summary, category_summary, daily_sales = aggregate(enriched)

        # Load
        load(enriched, customer_summary, category_summary, daily_sales)

        logger.info("=" * 50)
        logger.info("ETL パイプライン完了")
        logger.info("=" * 50)
    except Exception:
        logger.exception("ETLパイプラインでエラーが発生しました")
        raise


if __name__ == "__main__":
    main()
