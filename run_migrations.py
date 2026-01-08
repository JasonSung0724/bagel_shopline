"""
Database Migration Runner
執行 migrations 資料夾中的 SQL migration 檔案
"""
import os
import sys
import io
import psycopg2
from pathlib import Path

# 修正 Windows 編碼問題
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from loguru import logger

# 設定 logger
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


def get_database_url():
    """從環境變數取得資料庫連線 URL"""
    # 優先使用環境變數
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url

    # 從 .env 讀取
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url

    # 使用預設 Supabase 連線
    # postgresql://postgres:password@host:port/postgres
    logger.error("找不到 DATABASE_URL 環境變數")
    logger.info("請設定 DATABASE_URL 環境變數或在 .env 檔案中加入：")
    logger.info("DATABASE_URL=postgresql://postgres:password@host:port/postgres")
    sys.exit(1)


def get_migration_files(migrations_dir: Path):
    """取得所有 migration 檔案，按編號排序"""
    if not migrations_dir.exists():
        logger.error(f"migrations 資料夾不存在: {migrations_dir}")
        sys.exit(1)

    sql_files = sorted(migrations_dir.glob('*.sql'))

    if not sql_files:
        logger.warning("沒有找到任何 migration 檔案")
        return []

    return sql_files


def run_migration(conn, migration_file: Path):
    """執行單個 migration 檔案"""
    logger.info(f"執行 migration: {migration_file.name}")

    try:
        # 讀取 SQL 檔案
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        # 執行 SQL
        with conn.cursor() as cur:
            cur.execute(sql)

        conn.commit()
        logger.success(f"{migration_file.name} 執行成功")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"{migration_file.name} 執行失敗: {e}")
        return False


def main():
    """主程式"""
    logger.info("=" * 80)
    logger.info("開始執行 Database Migrations")
    logger.info("=" * 80)

    # 取得資料庫連線
    db_url = get_database_url()
    logger.info(f"連線資料庫...")

    try:
        conn = psycopg2.connect(db_url)
        logger.success("資料庫連線成功")
    except Exception as e:
        logger.error(f"資料庫連線失敗: {e}")
        sys.exit(1)

    # 取得 migration 檔案
    migrations_dir = Path(__file__).parent / 'migrations'
    migration_files = get_migration_files(migrations_dir)

    if not migration_files:
        logger.info("沒有需要執行的 migrations")
        conn.close()
        return

    logger.info(f"找到 {len(migration_files)} 個 migration 檔案")

    # 執行每個 migration
    success_count = 0
    fail_count = 0

    for migration_file in migration_files:
        if run_migration(conn, migration_file):
            success_count += 1
        else:
            fail_count += 1

    # 關閉連線
    conn.close()

    # 顯示結果
    logger.info("=" * 80)
    logger.info(f"成功: {success_count} 個")
    logger.info(f"失敗: {fail_count} 個")

    if fail_count > 0:
        logger.error("Migrations 執行有失敗")
        sys.exit(1)
    else:
        logger.success("所有 Migrations 執行成功！")


if __name__ == "__main__":
    main()
