"""Fills the database with sample categories and products. Safe to run more than once."""
import re
from decimal import Decimal

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Category, Product

CATEGORIES = ["Bedding", "Clothes", "Kitchen", "Decor"]
PRODUCTS = [
    ("Bedding", "Cotton duvet set", 4800, "6x6, with 2 pillowcases"),
    ("Bedding", "Fleece blanket", 2200, "Warm and light, double size"),
    ("Bedding", "Pillow pair", 1500, "Soft fibre filling"),
    ("Bedding", "Fitted sheet set", 2600, "Percale cotton, 3 pieces"),
    ("Clothes", "Kitenge dress", 2500, "Tailored, sizes S to XL"),
    ("Clothes", "Kaftan shirt", 1800, "Breathable cotton"),
    ("Clothes", "Maasai shuka wrap", 900, "Classic red check"),
    ("Clothes", "Everyday hoodie", 2200, "Brushed inside, unisex"),
    ("Kitchen", "Sufuria set (3 pcs)", 2900, "Stainless steel with lids"),
    ("Kitchen", "Wooden spoon set", 750, "Set of 5, hand finished"),
    ("Kitchen", "Chopping board", 1100, "Solid acacia wood"),
    ("Kitchen", "Mug set (6)", 1300, "Ceramic, 300 ml"),
    ("Decor", "Woven basket", 1400, "Sisal, handmade in Kenya"),
    ("Decor", "Ceramic vase", 1900, "Matte glaze, 30 cm"),
    ("Decor", "Cushion cover", 600, "45x45 cm, zip closure"),
    ("Decor", "Wall mirror", 3200, "Round, rope frame"),
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    with SessionLocal() as db:
        cats = {}
        for name in CATEGORIES:
            cat = db.scalar(select(Category).where(Category.slug == slugify(name)))
            if not cat:
                cat = Category(name=name, slug=slugify(name))
                db.add(cat)
                db.flush()
            cats[name] = cat
        added = 0
        for cat_name, name, price, desc in PRODUCTS:
            if not db.scalar(select(Product).where(Product.slug == slugify(name))):
                db.add(Product(category_id=cats[cat_name].id, name=name, slug=slugify(name),
                               description=desc, price=Decimal(price), stock_quantity=20))
                added += 1
        db.commit()
        print(f"Seed complete: {added} products added.")


if __name__ == "__main__":
    main()
