# Python ETL サンプルプロジェクト

Python + Pandas を使用したETL（Extract, Transform, Load）サンプルプロジェクトです。

## 処理フロー

1. **Extract** - `data/raw/` から CSV ファイルを読み込む
2. **Transform** - データのクレンジング・結合・集計を行う
3. **Load** - 加工結果を `data/processed/` へ CSV 出力する

## セットアップ

### 必要な環境

- Python 3.12以上
- uv (パッケージマネージャー)

### インストール

```bash
# 依存関係のインストール
uv sync

# 開発依存関係も含めてインストール
uv sync --all-extras
```

## 使用方法

### ETLパイプラインの実行

```bash
uv run python src/python_etl/etl.py
```

### テストの実行

```bash
# すべてのテストを実行
uv run pytest

# カバレッジレポート付きで実行
uv run pytest --cov=src/python_etl --cov-report=html
```

### コードフォーマット

```bash
# フォーマット
uv run ruff format .

# Lintチェック
uv run ruff check .

# Lintの自動修正
uv run ruff check . --fix
```

### 型チェック

```bash
uv run pyright
```

## プロジェクト構造

```
python-etl/
├── src/
│   └── python_etl/
│       ├── __init__.py
│       └── etl.py
├── tests/
│   ├── __init__.py
│   └── test_etl.py
├── data/
│   ├── raw/           # 入力データ
│   └── processed/     # 出力データ
├── pyproject.toml
├── CLAUDE.md          # 開発ガイドライン
└── README.md
```

## 開発ガイドライン

プロジェクトの詳細な開発ルールについては、[CLAUDE.md](./CLAUDE.md) を参照してください。

## ライセンス

MIT License
