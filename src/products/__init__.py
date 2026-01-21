"""
Products Module - Product Catalog Management
=============================================
Manage product catalog for quotes and deals.
"""

from .product_service import (
    ProductService,
    Product,
    ProductCategory,
    PriceBook,
    PriceBookEntry,
    get_product_service,
)

__all__ = [
    "ProductService",
    "Product",
    "ProductCategory",
    "PriceBook",
    "PriceBookEntry",
    "get_product_service",
]
