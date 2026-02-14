"""
Python + Pandas ETL サンプルプロジェクト

処理フロー:
  1. Extract  - data/raw/ から CSV ファイルを読み込む
  2. Transform - データのクレンジング・結合・集計を行う
  3. Load     - 加工結果を data/processed/ へ CSV 出力する
"""

import logging
from typing import Final

from python_etl.extract import extract
from python_etl.load import load
from python_etl.transform import aggregate, clean_customers, clean_sales, merge_and_enrich

# ロガーの設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger: Final[logging.Logger] = logging.getLogger(__name__)


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
