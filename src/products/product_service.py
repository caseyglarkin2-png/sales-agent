"""
Product Service - Product Catalog Management
=============================================
Handles products, pricing, and catalog management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class ProductType(str, Enum):
    """Product type values."""
    PRODUCT = "product"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    BUNDLE = "bundle"


class ProductStatus(str, Enum):
    """Product status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"
    COMING_SOON = "coming_soon"


class BillingFrequency(str, Enum):
    """Billing frequency for subscriptions."""
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class PricingModel(str, Enum):
    """Pricing model types."""
    FLAT = "flat"
    TIERED = "tiered"
    VOLUME = "volume"
    PER_UNIT = "per_unit"
    CUSTOM = "custom"


@dataclass
class PriceTier:
    """A pricing tier for tiered/volume pricing."""
    id: str
    min_quantity: int
    max_quantity: Optional[int]  # None for unlimited
    unit_price: float
    flat_fee: float = 0.0


@dataclass
class ProductCategory:
    """A product category."""
    id: str
    name: str
    description: str
    parent_id: Optional[str] = None
    display_order: int = 0
    is_active: bool = True
    icon: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Product:
    """A product in the catalog."""
    id: str
    name: str
    description: str
    sku: str
    
    # Classification
    product_type: ProductType = ProductType.PRODUCT
    status: ProductStatus = ProductStatus.ACTIVE
    category_id: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    
    # Pricing
    base_price: float = 0.0
    cost: float = 0.0  # Cost to company
    currency: str = "USD"
    pricing_model: PricingModel = PricingModel.FLAT
    price_tiers: list[PriceTier] = field(default_factory=list)
    
    # Subscription settings
    billing_frequency: BillingFrequency = BillingFrequency.ONE_TIME
    setup_fee: float = 0.0
    trial_days: int = 0
    
    # Units
    unit_name: str = "unit"
    unit_plural: str = "units"
    min_quantity: int = 1
    max_quantity: Optional[int] = None
    quantity_step: int = 1
    
    # Tax
    taxable: bool = True
    tax_code: Optional[str] = None
    
    # Display
    image_url: Optional[str] = None
    short_description: Optional[str] = None
    features: list[str] = field(default_factory=list)
    
    # Bundle
    is_bundle: bool = False
    bundle_items: list[dict[str, Any]] = field(default_factory=list)  # {product_id, quantity}
    
    # Metadata
    external_id: Optional[str] = None
    custom_fields: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_price(self, quantity: int = 1) -> float:
        """Calculate price for a given quantity."""
        if self.pricing_model == PricingModel.FLAT:
            return self.base_price
        
        if self.pricing_model == PricingModel.PER_UNIT:
            return self.base_price * quantity
        
        if self.pricing_model == PricingModel.TIERED:
            # Each tier applies to its range
            total = 0.0
            remaining = quantity
            for tier in sorted(self.price_tiers, key=lambda t: t.min_quantity):
                if remaining <= 0:
                    break
                tier_max = tier.max_quantity or float('inf')
                tier_quantity = min(remaining, tier_max - tier.min_quantity + 1)
                total += tier_quantity * tier.unit_price + tier.flat_fee
                remaining -= tier_quantity
            return total
        
        if self.pricing_model == PricingModel.VOLUME:
            # Entire quantity gets volume price
            for tier in sorted(self.price_tiers, key=lambda t: t.min_quantity, reverse=True):
                if quantity >= tier.min_quantity:
                    return quantity * tier.unit_price + tier.flat_fee
            return self.base_price * quantity
        
        return self.base_price * quantity


@dataclass
class PriceBookEntry:
    """An entry in a price book."""
    id: str
    price_book_id: str
    product_id: str
    unit_price: float
    min_quantity: int = 1
    max_quantity: Optional[int] = None
    discount_percentage: float = 0.0
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PriceBook:
    """A price book for customer-specific pricing."""
    id: str
    name: str
    description: str
    is_standard: bool = False
    is_active: bool = True
    currency: str = "USD"
    entries: list[PriceBookEntry] = field(default_factory=list)
    
    # Assignment
    customer_ids: list[str] = field(default_factory=list)  # Companies using this price book
    segment_ids: list[str] = field(default_factory=list)  # Segments using this price book
    
    # Validity
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class ProductService:
    """Service for managing products and pricing."""
    
    def __init__(self):
        self.products: dict[str, Product] = {}
        self.categories: dict[str, ProductCategory] = {}
        self.price_books: dict[str, PriceBook] = {}
        self._sku_counter: int = 1000
        self._init_sample_data()
    
    def _init_sample_data(self) -> None:
        """Initialize sample products."""
        # Create categories
        software_cat = ProductCategory(
            id="cat-software",
            name="Software",
            description="Software products and subscriptions",
        )
        services_cat = ProductCategory(
            id="cat-services",
            name="Services",
            description="Professional services",
        )
        self.categories[software_cat.id] = software_cat
        self.categories[services_cat.id] = services_cat
        
        # Create standard price book
        standard_pb = PriceBook(
            id="pb-standard",
            name="Standard Price Book",
            description="Default pricing",
            is_standard=True,
        )
        self.price_books[standard_pb.id] = standard_pb
    
    def _generate_sku(self) -> str:
        """Generate unique SKU."""
        self._sku_counter += 1
        return f"SKU-{self._sku_counter}"
    
    # Product CRUD
    async def create_product(
        self,
        name: str,
        description: str,
        base_price: float,
        sku: Optional[str] = None,
        **kwargs
    ) -> Product:
        """Create a new product."""
        product_id = str(uuid.uuid4())
        
        product = Product(
            id=product_id,
            name=name,
            description=description,
            sku=sku or self._generate_sku(),
            base_price=base_price,
            **kwargs
        )
        
        self.products[product_id] = product
        return product
    
    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product by ID."""
        return self.products.get(product_id)
    
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU."""
        for product in self.products.values():
            if product.sku == sku:
                return product
        return None
    
    async def update_product(
        self,
        product_id: str,
        updates: dict[str, Any]
    ) -> Optional[Product]:
        """Update a product."""
        product = self.products.get(product_id)
        if not product:
            return None
        
        for key, value in updates.items():
            if hasattr(product, key):
                setattr(product, key, value)
        
        product.updated_at = datetime.utcnow()
        return product
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete a product."""
        if product_id in self.products:
            del self.products[product_id]
            return True
        return False
    
    async def list_products(
        self,
        category_id: Optional[str] = None,
        product_type: Optional[ProductType] = None,
        status: Optional[ProductStatus] = None,
        search: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Product]:
        """List products with filters."""
        products = list(self.products.values())
        
        if category_id:
            products = [p for p in products if p.category_id == category_id]
        if product_type:
            products = [p for p in products if p.product_type == product_type]
        if status:
            products = [p for p in products if p.status == status]
        if search:
            search_lower = search.lower()
            products = [
                p for p in products
                if search_lower in p.name.lower()
                or search_lower in p.description.lower()
                or search_lower in p.sku.lower()
            ]
        if tags:
            products = [p for p in products if any(t in p.tags for t in tags)]
        
        # Sort by name
        products.sort(key=lambda p: p.name)
        
        return products[offset:offset + limit]
    
    # Price tiers
    async def add_price_tier(
        self,
        product_id: str,
        min_quantity: int,
        max_quantity: Optional[int],
        unit_price: float,
        flat_fee: float = 0.0
    ) -> Optional[PriceTier]:
        """Add a price tier to a product."""
        product = self.products.get(product_id)
        if not product:
            return None
        
        tier = PriceTier(
            id=str(uuid.uuid4()),
            min_quantity=min_quantity,
            max_quantity=max_quantity,
            unit_price=unit_price,
            flat_fee=flat_fee,
        )
        
        product.price_tiers.append(tier)
        product.updated_at = datetime.utcnow()
        
        return tier
    
    async def remove_price_tier(self, product_id: str, tier_id: str) -> bool:
        """Remove a price tier."""
        product = self.products.get(product_id)
        if not product:
            return False
        
        original_count = len(product.price_tiers)
        product.price_tiers = [t for t in product.price_tiers if t.id != tier_id]
        
        if len(product.price_tiers) < original_count:
            product.updated_at = datetime.utcnow()
            return True
        
        return False
    
    # Categories
    async def create_category(
        self,
        name: str,
        description: str,
        parent_id: Optional[str] = None,
        **kwargs
    ) -> ProductCategory:
        """Create a product category."""
        category = ProductCategory(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            parent_id=parent_id,
            **kwargs
        )
        self.categories[category.id] = category
        return category
    
    async def list_categories(
        self,
        parent_id: Optional[str] = None,
        active_only: bool = True
    ) -> list[ProductCategory]:
        """List categories."""
        categories = list(self.categories.values())
        
        if parent_id is not None:
            categories = [c for c in categories if c.parent_id == parent_id]
        if active_only:
            categories = [c for c in categories if c.is_active]
        
        categories.sort(key=lambda c: (c.display_order, c.name))
        
        return categories
    
    async def get_category(self, category_id: str) -> Optional[ProductCategory]:
        """Get a category by ID."""
        return self.categories.get(category_id)
    
    async def update_category(
        self,
        category_id: str,
        updates: dict[str, Any]
    ) -> Optional[ProductCategory]:
        """Update a category."""
        category = self.categories.get(category_id)
        if not category:
            return None
        
        for key, value in updates.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        category.updated_at = datetime.utcnow()
        return category
    
    async def delete_category(self, category_id: str) -> bool:
        """Delete a category."""
        if category_id in self.categories:
            # Move products to no category
            for product in self.products.values():
                if product.category_id == category_id:
                    product.category_id = None
            del self.categories[category_id]
            return True
        return False
    
    async def get_category_tree(self) -> list[dict[str, Any]]:
        """Get hierarchical category tree."""
        root_categories = [c for c in self.categories.values() if c.parent_id is None]
        
        def build_tree(category: ProductCategory) -> dict[str, Any]:
            children = [
                c for c in self.categories.values()
                if c.parent_id == category.id
            ]
            return {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "children": [build_tree(c) for c in children],
            }
        
        return [build_tree(c) for c in root_categories]
    
    # Price Books
    async def create_price_book(
        self,
        name: str,
        description: str,
        **kwargs
    ) -> PriceBook:
        """Create a price book."""
        price_book = PriceBook(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            **kwargs
        )
        self.price_books[price_book.id] = price_book
        return price_book
    
    async def get_price_book(self, price_book_id: str) -> Optional[PriceBook]:
        """Get a price book by ID."""
        return self.price_books.get(price_book_id)
    
    async def list_price_books(self, active_only: bool = True) -> list[PriceBook]:
        """List price books."""
        price_books = list(self.price_books.values())
        if active_only:
            price_books = [pb for pb in price_books if pb.is_active]
        return price_books
    
    async def add_price_book_entry(
        self,
        price_book_id: str,
        product_id: str,
        unit_price: float,
        **kwargs
    ) -> Optional[PriceBookEntry]:
        """Add an entry to a price book."""
        price_book = self.price_books.get(price_book_id)
        if not price_book:
            return None
        
        entry = PriceBookEntry(
            id=str(uuid.uuid4()),
            price_book_id=price_book_id,
            product_id=product_id,
            unit_price=unit_price,
            **kwargs
        )
        
        price_book.entries.append(entry)
        price_book.updated_at = datetime.utcnow()
        
        return entry
    
    async def get_price_for_customer(
        self,
        product_id: str,
        customer_id: str,
        quantity: int = 1
    ) -> Optional[float]:
        """Get price for a specific customer."""
        product = self.products.get(product_id)
        if not product:
            return None
        
        # Find applicable price book
        for price_book in self.price_books.values():
            if not price_book.is_active:
                continue
            if customer_id in price_book.customer_ids:
                # Find entry for product
                for entry in price_book.entries:
                    if entry.product_id == product_id and entry.is_active:
                        price = entry.unit_price * quantity
                        if entry.discount_percentage > 0:
                            price *= (1 - entry.discount_percentage / 100)
                        return price
        
        # Fall back to standard pricing
        return product.get_price(quantity)
    
    # Bundle management
    async def create_bundle(
        self,
        name: str,
        description: str,
        items: list[dict[str, Any]],  # [{product_id, quantity}]
        **kwargs
    ) -> Product:
        """Create a product bundle."""
        # Calculate bundle price
        total_price = 0.0
        for item in items:
            product = self.products.get(item["product_id"])
            if product:
                total_price += product.get_price(item.get("quantity", 1))
        
        bundle = await self.create_product(
            name=name,
            description=description,
            base_price=kwargs.get("base_price", total_price),
            product_type=ProductType.BUNDLE,
            is_bundle=True,
            bundle_items=items,
            **{k: v for k, v in kwargs.items() if k != "base_price"}
        )
        
        return bundle
    
    async def get_bundle_contents(self, bundle_id: str) -> list[dict[str, Any]]:
        """Get contents of a bundle."""
        bundle = self.products.get(bundle_id)
        if not bundle or not bundle.is_bundle:
            return []
        
        contents = []
        for item in bundle.bundle_items:
            product = self.products.get(item["product_id"])
            if product:
                contents.append({
                    "product": {
                        "id": product.id,
                        "name": product.name,
                        "sku": product.sku,
                        "base_price": product.base_price,
                    },
                    "quantity": item.get("quantity", 1),
                })
        
        return contents
    
    # Search and analytics
    async def search_products(self, query: str, limit: int = 20) -> list[Product]:
        """Full-text search for products."""
        query_lower = query.lower()
        
        scored_products = []
        for product in self.products.values():
            score = 0
            
            # Name match (highest priority)
            if query_lower in product.name.lower():
                score += 10
                if product.name.lower().startswith(query_lower):
                    score += 5
            
            # SKU match
            if query_lower in product.sku.lower():
                score += 8
            
            # Description match
            if query_lower in product.description.lower():
                score += 3
            
            # Tag match
            for tag in product.tags:
                if query_lower in tag.lower():
                    score += 2
            
            if score > 0:
                scored_products.append((product, score))
        
        # Sort by score
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        return [p[0] for p in scored_products[:limit]]
    
    async def get_product_stats(self) -> dict[str, Any]:
        """Get product catalog statistics."""
        products = list(self.products.values())
        
        by_type = {}
        by_status = {}
        by_category = {}
        
        for p in products:
            ptype = p.product_type.value
            by_type[ptype] = by_type.get(ptype, 0) + 1
            
            status = p.status.value
            by_status[status] = by_status.get(status, 0) + 1
            
            cat = p.category_id or "uncategorized"
            by_category[cat] = by_category.get(cat, 0) + 1
        
        prices = [p.base_price for p in products if p.base_price > 0]
        
        return {
            "total_products": len(products),
            "active_products": sum(1 for p in products if p.status == ProductStatus.ACTIVE),
            "by_type": by_type,
            "by_status": by_status,
            "by_category": by_category,
            "total_categories": len(self.categories),
            "total_price_books": len(self.price_books),
            "avg_price": sum(prices) / len(prices) if prices else 0,
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
        }
    
    # Import/Export
    async def export_catalog(self) -> dict[str, Any]:
        """Export entire catalog."""
        return {
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "sku": p.sku,
                    "product_type": p.product_type.value,
                    "status": p.status.value,
                    "base_price": p.base_price,
                    "category_id": p.category_id,
                    "tags": p.tags,
                }
                for p in self.products.values()
            ],
            "categories": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "parent_id": c.parent_id,
                }
                for c in self.categories.values()
            ],
            "exported_at": datetime.utcnow().isoformat(),
        }


# Singleton instance
_product_service: Optional[ProductService] = None


def get_product_service() -> ProductService:
    """Get product service singleton."""
    global _product_service
    if _product_service is None:
        _product_service = ProductService()
    return _product_service
