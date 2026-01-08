"""
SQLAlchemy Database Models for Sales System
用於 Alembic migrations
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Date, Boolean, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class MasterSalesProduct(Base):
    """銷量商品主檔 - 記錄所有曾經出現的商品"""

    __tablename__ = 'master_sales_products'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_name = Column(String, unique=True, nullable=False, index=True)
    category = Column(String, index=True)  # 'bread' or 'box'
    first_seen_date = Column(Date)  # 第一次出現的日期
    last_seen_date = Column(Date)   # 最後一次出現的日期
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MasterSalesProduct(name={self.product_name}, category={self.category})>"


class DailySales(Base):
    """每日銷量記錄 - 記錄每天每個商品的實際銷量"""

    __tablename__ = 'daily_sales'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_date = Column(Date, nullable=False, index=True)
    product_name = Column(String, nullable=False, index=True)
    category = Column(String, index=True)  # 'bread' or 'box'
    quantity = Column(Float, nullable=False, default=0)  # 實出量（可以是 0）
    source = Column(String, default='flowtide_qc')  # 資料來源
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('sale_date', 'product_name', name='uq_daily_sales_date_product'),
    )

    def __repr__(self):
        return f"<DailySales(date={self.sale_date}, product={self.product_name}, qty={self.quantity})>"
