"""
Products Routes - Product Catalog API
======================================
REST API for products and pricing.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Any

from src.products.product_service import (
    get_product_service,
    ProductType,
    ProductStatus,
    PricingModel,
    BillingFrequency,
)

router = APIRouter(prefix="/products", tags=["products"])


class CreateProductRequest(BaseModel):
    """Request to create a product."""
    name: str
    description: str
    base_price: float
    sku: Optional[str] = None
    product_type: str = "product"
    category_id: Optional[str] = None
    tags: list[str] = []
    cost: float = 0.0
    currency: str = "USD"
    pricing_model: str = "flat"
    billing_frequency: str = "one_time"
    setup_fee: float = 0.0
    unit_name: str = "unit"
    taxable: bool = True
    features: list[str] = []


class UpdateProductRequest(BaseModel):
    """Request to update a product."""
    name: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[float] = None
    status: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[list[str]] = None
    cost: Optional[float] = None
    pricing_model: Optional[str] = None
    taxable: Optional[bool] = None
    features: Optional[list[str]] = None


class AddPriceTierRequest(BaseModel):
    """Request to add a price tier."""
    min_quantity: int
    max_quantity: Optional[int] = None
    unit_price: float
    flat_fee: float = 0.0


class CreateCategoryRequest(BaseModel):
    """Request to create a category."""
    name: str
    description: str
    parent_id: Optional[str] = None
    display_order: int = 0
    icon: Optional[str] = None


class UpdateCategoryRequest(BaseModel):
    """Request to update a category."""
    name: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    icon: Optional[str] = None


class CreatePriceBookRequest(BaseModel):
    """Request to create a price book."""
    name: str
    description: str
    currency: str = "USD"
    customer_ids: list[str] = []


class AddPriceBookEntryRequest(BaseModel):
    """Request to add a price book entry."""
    product_id: str
    unit_price: float
    min_quantity: int = 1
    max_quantity: Optional[int] = None
    discount_percentage: float = 0.0


class CreateBundleRequest(BaseModel):
    """Request to create a bundle."""
    name: str
    description: str
    items: list[dict[str, Any]]  # [{product_id, quantity}]
    base_price: Optional[float] = None
    category_id: Optional[str] = None
    tags: list[str] = []


class GetPriceRequest(BaseModel):
    """Request to get price for customer."""
    product_id: str
    customer_id: str
    quantity: int = 1


def product_to_dict(product) -> dict:
    """Convert product to dictionary."""
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "sku": product.sku,
        "product_type": product.product_type.value,
        "status": product.status.value,
        "category_id": product.category_id,
        "tags": product.tags,
        "base_price": product.base_price,
        "cost": product.cost,
        "currency": product.currency,
        "pricing_model": product.pricing_model.value,
        "price_tiers": [
            {
                "id": t.id,
                "min_quantity": t.min_quantity,
                "max_quantity": t.max_quantity,
                "unit_price": t.unit_price,
                "flat_fee": t.flat_fee,
            }
            for t in product.price_tiers
        ],
        "billing_frequency": product.billing_frequency.value,
        "setup_fee": product.setup_fee,
        "trial_days": product.trial_days,
        "unit_name": product.unit_name,
        "unit_plural": product.unit_plural,
        "min_quantity": product.min_quantity,
        "max_quantity": product.max_quantity,
        "taxable": product.taxable,
        "tax_code": product.tax_code,
        "image_url": product.image_url,
        "short_description": product.short_description,
        "features": product.features,
        "is_bundle": product.is_bundle,
        "bundle_items": product.bundle_items,
        "created_at": product.created_at.isoformat(),
        "updated_at": product.updated_at.isoformat(),
    }


@router.post("")
async def create_product(request: CreateProductRequest):
    """Create a new product."""
    service = get_product_service()
    
    product = await service.create_product(
        name=request.name,
        description=request.description,
        base_price=request.base_price,
        sku=request.sku,
        product_type=ProductType(request.product_type),
        category_id=request.category_id,
        tags=request.tags,
        cost=request.cost,
        currency=request.currency,
        pricing_model=PricingModel(request.pricing_model),
        billing_frequency=BillingFrequency(request.billing_frequency),
        setup_fee=request.setup_fee,
        unit_name=request.unit_name,
        taxable=request.taxable,
        features=request.features,
    )
    
    return {"product": product_to_dict(product)}


@router.get("")
async def list_products(
    category_id: Optional[str] = None,
    product_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[str] = None,  # comma-separated
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0)
):
    """List products with filters."""
    service = get_product_service()
    
    type_enum = ProductType(product_type) if product_type else None
    status_enum = ProductStatus(status) if status else None
    tag_list = tags.split(",") if tags else None
    
    products = await service.list_products(
        category_id=category_id,
        product_type=type_enum,
        status=status_enum,
        search=search,
        tags=tag_list,
        limit=limit,
        offset=offset
    )
    
    return {
        "products": [product_to_dict(p) for p in products],
        "count": len(products)
    }


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, le=50)
):
    """Search products."""
    service = get_product_service()
    
    products = await service.search_products(q, limit)
    
    return {
        "products": [product_to_dict(p) for p in products],
        "count": len(products)
    }


@router.get("/stats")
async def get_product_stats():
    """Get product catalog statistics."""
    service = get_product_service()
    
    stats = await service.get_product_stats()
    
    return stats


@router.get("/export")
async def export_catalog():
    """Export product catalog."""
    service = get_product_service()
    
    export_data = await service.export_catalog()
    
    return export_data


# Categories
@router.get("/categories")
async def list_categories(
    parent_id: Optional[str] = None,
    active_only: bool = True
):
    """List product categories."""
    service = get_product_service()
    
    categories = await service.list_categories(
        parent_id=parent_id,
        active_only=active_only
    )
    
    return {
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "parent_id": c.parent_id,
                "display_order": c.display_order,
                "is_active": c.is_active,
                "icon": c.icon,
            }
            for c in categories
        ]
    }


@router.get("/categories/tree")
async def get_category_tree():
    """Get hierarchical category tree."""
    service = get_product_service()
    
    tree = await service.get_category_tree()
    
    return {"tree": tree}


@router.post("/categories")
async def create_category(request: CreateCategoryRequest):
    """Create a product category."""
    service = get_product_service()
    
    category = await service.create_category(
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
        display_order=request.display_order,
        icon=request.icon,
    )
    
    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "parent_id": category.parent_id,
        }
    }


@router.get("/categories/{category_id}")
async def get_category(category_id: str):
    """Get a category by ID."""
    service = get_product_service()
    
    category = await service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "parent_id": category.parent_id,
            "display_order": category.display_order,
            "is_active": category.is_active,
            "icon": category.icon,
        }
    }


@router.put("/categories/{category_id}")
async def update_category(category_id: str, request: UpdateCategoryRequest):
    """Update a category."""
    service = get_product_service()
    
    updates = request.model_dump(exclude_none=True)
    category = await service.update_category(category_id, updates)
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return {
        "category": {
            "id": category.id,
            "name": category.name,
            "description": category.description,
        }
    }


@router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    """Delete a category."""
    service = get_product_service()
    
    success = await service.delete_category(category_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    
    return {"success": True}


# Price Books
@router.get("/price-books")
async def list_price_books(active_only: bool = True):
    """List price books."""
    service = get_product_service()
    
    price_books = await service.list_price_books(active_only=active_only)
    
    return {
        "price_books": [
            {
                "id": pb.id,
                "name": pb.name,
                "description": pb.description,
                "is_standard": pb.is_standard,
                "is_active": pb.is_active,
                "currency": pb.currency,
                "entry_count": len(pb.entries),
                "customer_count": len(pb.customer_ids),
            }
            for pb in price_books
        ]
    }


@router.post("/price-books")
async def create_price_book(request: CreatePriceBookRequest):
    """Create a price book."""
    service = get_product_service()
    
    price_book = await service.create_price_book(
        name=request.name,
        description=request.description,
        currency=request.currency,
        customer_ids=request.customer_ids,
    )
    
    return {
        "price_book": {
            "id": price_book.id,
            "name": price_book.name,
            "description": price_book.description,
        }
    }


@router.get("/price-books/{price_book_id}")
async def get_price_book(price_book_id: str):
    """Get a price book by ID."""
    service = get_product_service()
    
    price_book = await service.get_price_book(price_book_id)
    if not price_book:
        raise HTTPException(status_code=404, detail="Price book not found")
    
    return {
        "price_book": {
            "id": price_book.id,
            "name": price_book.name,
            "description": price_book.description,
            "is_standard": price_book.is_standard,
            "is_active": price_book.is_active,
            "currency": price_book.currency,
            "entries": [
                {
                    "id": e.id,
                    "product_id": e.product_id,
                    "unit_price": e.unit_price,
                    "min_quantity": e.min_quantity,
                    "max_quantity": e.max_quantity,
                    "discount_percentage": e.discount_percentage,
                }
                for e in price_book.entries
            ],
            "customer_ids": price_book.customer_ids,
        }
    }


@router.post("/price-books/{price_book_id}/entries")
async def add_price_book_entry(price_book_id: str, request: AddPriceBookEntryRequest):
    """Add an entry to a price book."""
    service = get_product_service()
    
    entry = await service.add_price_book_entry(
        price_book_id=price_book_id,
        product_id=request.product_id,
        unit_price=request.unit_price,
        min_quantity=request.min_quantity,
        max_quantity=request.max_quantity,
        discount_percentage=request.discount_percentage,
    )
    
    if not entry:
        raise HTTPException(status_code=404, detail="Price book not found")
    
    return {
        "entry": {
            "id": entry.id,
            "product_id": entry.product_id,
            "unit_price": entry.unit_price,
        }
    }


@router.post("/price-for-customer")
async def get_price_for_customer(request: GetPriceRequest):
    """Get price for a specific customer."""
    service = get_product_service()
    
    price = await service.get_price_for_customer(
        product_id=request.product_id,
        customer_id=request.customer_id,
        quantity=request.quantity
    )
    
    if price is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "product_id": request.product_id,
        "customer_id": request.customer_id,
        "quantity": request.quantity,
        "total_price": price,
        "unit_price": price / request.quantity if request.quantity > 0 else 0
    }


# Bundles
@router.post("/bundles")
async def create_bundle(request: CreateBundleRequest):
    """Create a product bundle."""
    service = get_product_service()
    
    kwargs = {}
    if request.base_price is not None:
        kwargs["base_price"] = request.base_price
    if request.category_id:
        kwargs["category_id"] = request.category_id
    if request.tags:
        kwargs["tags"] = request.tags
    
    bundle = await service.create_bundle(
        name=request.name,
        description=request.description,
        items=request.items,
        **kwargs
    )
    
    return {"product": product_to_dict(bundle)}


@router.get("/bundles/{bundle_id}/contents")
async def get_bundle_contents(bundle_id: str):
    """Get contents of a bundle."""
    service = get_product_service()
    
    contents = await service.get_bundle_contents(bundle_id)
    
    if not contents:
        raise HTTPException(status_code=404, detail="Bundle not found or empty")
    
    return {"contents": contents}


# Individual product routes
@router.get("/{product_id}")
async def get_product(product_id: str):
    """Get a product by ID."""
    service = get_product_service()
    
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"product": product_to_dict(product)}


@router.get("/sku/{sku}")
async def get_product_by_sku(sku: str):
    """Get a product by SKU."""
    service = get_product_service()
    
    product = await service.get_by_sku(sku)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"product": product_to_dict(product)}


@router.put("/{product_id}")
async def update_product(product_id: str, request: UpdateProductRequest):
    """Update a product."""
    service = get_product_service()
    
    updates = request.model_dump(exclude_none=True)
    
    if "status" in updates:
        updates["status"] = ProductStatus(updates["status"])
    if "pricing_model" in updates:
        updates["pricing_model"] = PricingModel(updates["pricing_model"])
    
    product = await service.update_product(product_id, updates)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"product": product_to_dict(product)}


@router.delete("/{product_id}")
async def delete_product(product_id: str):
    """Delete a product."""
    service = get_product_service()
    
    success = await service.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"success": True}


# Price tiers
@router.post("/{product_id}/price-tiers")
async def add_price_tier(product_id: str, request: AddPriceTierRequest):
    """Add a price tier to a product."""
    service = get_product_service()
    
    tier = await service.add_price_tier(
        product_id=product_id,
        min_quantity=request.min_quantity,
        max_quantity=request.max_quantity,
        unit_price=request.unit_price,
        flat_fee=request.flat_fee,
    )
    
    if not tier:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product = await service.get_product(product_id)
    
    return {"product": product_to_dict(product)}


@router.delete("/{product_id}/price-tiers/{tier_id}")
async def remove_price_tier(product_id: str, tier_id: str):
    """Remove a price tier."""
    service = get_product_service()
    
    success = await service.remove_price_tier(product_id, tier_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product or tier not found")
    
    product = await service.get_product(product_id)
    
    return {"product": product_to_dict(product)}


@router.get("/{product_id}/price")
async def get_product_price(
    product_id: str,
    quantity: int = Query(default=1, ge=1)
):
    """Get product price for a quantity."""
    service = get_product_service()
    
    product = await service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    price = product.get_price(quantity)
    
    return {
        "product_id": product_id,
        "quantity": quantity,
        "total_price": price,
        "unit_price": price / quantity if quantity > 0 else 0
    }
