"""
Main daily script for processing Flowtide orders.

This script:
1. Fetches Flowtide Excel from email
2. Updates C2C orders in Google Sheet
3. Updates ShopLine orders via API
4. Sends LINE notification

Usage:
    python main_scripts.py
"""
from src.utils.logger import setup_logger
from src.orchestrator.daily_workflow import DailyWorkflow
from loguru import logger


def main():
    """Run the daily order processing workflow."""
    # Setup logging
    setup_logger(log_file="logs/app.log")

    logger.info("=" * 50)
    logger.info("開始執行 main_scripts.py")
    logger.info("=" * 50)

    # Run workflow with customer notifications enabled
    workflow = DailyWorkflow(notify_customers=True)
    success = workflow.run()

    if success:
        logger.success("main_scripts.py 執行完成")
    else:
        logger.warning("main_scripts.py 執行完成（有警告）")

    return success


if __name__ == "__main__":
    main()
