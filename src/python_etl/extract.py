"""Extract処理 - CSVファイルからデータを読み込む。"""

import logging
import pathlib
from typing import Final

import pandas as pd

# ロガーの設定
logger: Final[logging.Logger] = logging.getLogger(__name__)

# ディレクトリパスの設定
BASE_DIR: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parent.parent.parent
RAW_DIR: Final[pathlib.Path] = BASE_DIR / "data" / "raw"


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
