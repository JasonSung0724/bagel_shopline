"""
Sub script for updating outstanding ShopLine orders.

This script:
1. Fetches all outstanding orders from ShopLine
2. Queries Tcat status for each order
3. Updates ShopLine order status

Usage:
    python sub_scripts.py
"""
from src.utils.logger import setup_logger
from src.orchestrator.outstanding_workflow import OutstandingOrderWorkflow
from loguru import logger


def main():
    """Run the outstanding order update workflow."""
    # Setup logging
    setup_logger(log_file="logs/sub.log")

    logger.info("=" * 50)
    logger.info("開始執行 sub_scripts.py")
    logger.info("=" * 50)

    # Run workflow with customer notifications enabled
    workflow = OutstandingOrderWorkflow(notify_customers=True)
    success = workflow.run()

    if success:
        logger.success("sub_scripts.py 執行完成")
    else:
        logger.warning("sub_scripts.py 執行完成（有警告）")

    return success


if __name__ == "__main__":
    main()
