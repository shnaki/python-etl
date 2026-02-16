"""Load処理 - 加工結果をCSVファイルに出力する。"""

import logging
import pathlib
from typing import Final

import pandas as pd

# ロガーの設定
logger: Final[logging.Logger] = logging.getLogger(__name__)

# ディレクトリパスの設定
BASE_DIR: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parent.parent.parent
OUT_DIR: Final[pathlib.Path] = BASE_DIR / "data" / "processed"


def load(
    enriched: pd.DataFrame,
    customer_summary: pd.DataFrame,
    category_summary: pd.DataFrame,
    daily_sales: pd.DataFrame,
    *,
    out_dir: pathlib.Path | None = None,
) -> None:
    """
    加工結果を CSV に出力する。

    Args:
        enriched: エンリッチされた売上DataFrame
        customer_summary: 顧客別サマリーDataFrame
        category_summary: カテゴリ別サマリーDataFrame
        daily_sales: 日別売上DataFrame
        out_dir: 出力先ディレクトリ。Noneの場合はデフォルトの OUT_DIR を使用する。

    Raises:
        OSError: ディレクトリの作成やファイルの書き込みに失敗した場合
        PermissionError: ファイルへのアクセス権限がない場合
    """
    target_dir = out_dir if out_dir is not None else OUT_DIR
    try:
        target_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, pd.DataFrame] = {
            "sales_enriched.csv": enriched,
            "customer_summary.csv": customer_summary,
            "category_summary.csv": category_summary,
            "daily_sales.csv": daily_sales,
        }
        for filename, df in files.items():
            path = target_dir / filename
            df.to_csv(path, index=False, encoding="utf-8-sig")
            logger.info(f"[Load] {path} ({len(df)}件)")
    except (OSError, PermissionError):
        logger.exception("ファイルの書き込みに失敗しました")
        raise
