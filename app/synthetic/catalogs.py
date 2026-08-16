"""Curated NexaCommerce product catalog and Brazilian name lists."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.synthetic.rng import SeededRNG

FIRST_NAMES = [
    "Ana",
    "Bruno",
    "Camila",
    "Diego",
    "Eduarda",
    "Felipe",
    "Gabriela",
    "Henrique",
    "Isabela",
    "Joao",
    "Karina",
    "Lucas",
    "Mariana",
    "Nicolas",
    "Olivia",
    "Pedro",
    "Rafaela",
    "Sofia",
    "Thiago",
    "Vanessa",
]

LAST_NAMES = [
    "Almeida",
    "Barbosa",
    "Cardoso",
    "Dias",
    "Fernandes",
    "Gomes",
    "Lima",
    "Martins",
    "Nogueira",
    "Oliveira",
    "Pereira",
    "Rocha",
    "Santos",
    "Souza",
    "Teixeira",
]

PRODUCT_SPECS: list[dict[str, Any]] = [
    {
        "sku": "NX-PHN-01",
        "name": "NexaPhone 12",
        "category": "smartphones",
        "unit_price": "1899.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-PHN-02",
        "name": "NexaPhone Mini",
        "category": "smartphones",
        "unit_price": "1299.00",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-PHN-03",
        "name": "NexaPhone Outlet",
        "category": "smartphones",
        "unit_price": "799.90",
        "final_sale": True,
        "warranty_days": 90,
    },
    {
        "sku": "NX-LTP-01",
        "name": "NexaBook Pro 14",
        "category": "laptops",
        "unit_price": "5499.00",
        "final_sale": False,
        "warranty_days": 365,
    },
    {
        "sku": "NX-LTP-02",
        "name": "NexaBook Air 13",
        "category": "laptops",
        "unit_price": "3499.00",
        "final_sale": False,
        "warranty_days": 365,
    },
    {
        "sku": "NX-LTP-03",
        "name": "NexaBook Clearance 15",
        "category": "laptops",
        "unit_price": "2199.00",
        "final_sale": True,
        "warranty_days": 365,
    },
    {
        "sku": "NX-MON-01",
        "name": "NexaView 27 4K",
        "category": "monitors",
        "unit_price": "1899.00",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-MON-02",
        "name": "NexaView 24 FHD",
        "category": "monitors",
        "unit_price": "899.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-MON-03",
        "name": "NexaView Outlet 22",
        "category": "monitors",
        "unit_price": "449.90",
        "final_sale": True,
        "warranty_days": 90,
    },
    {
        "sku": "NX-HP-01",
        "name": "NexaSound ANC",
        "category": "headphones",
        "unit_price": "699.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-HP-02",
        "name": "NexaBuds",
        "category": "headphones",
        "unit_price": "249.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-HP-03",
        "name": "NexaBuds Lite",
        "category": "headphones",
        "unit_price": "99.90",
        "final_sale": True,
        "warranty_days": 90,
    },
    {
        "sku": "NX-KB-01",
        "name": "NexaKey Mechanical",
        "category": "keyboards",
        "unit_price": "499.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-KB-02",
        "name": "NexaKey Wireless",
        "category": "keyboards",
        "unit_price": "299.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-KB-03",
        "name": "NexaKey Compact",
        "category": "keyboards",
        "unit_price": "149.90",
        "final_sale": True,
        "warranty_days": 90,
    },
    {
        "sku": "NX-ACC-01",
        "name": "NexaCharge 65W",
        "category": "accessories",
        "unit_price": "189.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-ACC-02",
        "name": "USB-C Hub 7-in-1",
        "category": "accessories",
        "unit_price": "249.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-ACC-03",
        "name": "NexaCase Phone",
        "category": "accessories",
        "unit_price": "79.90",
        "final_sale": True,
        "warranty_days": 90,
    },
    {
        "sku": "NX-ACC-04",
        "name": "NexaMouse Silent",
        "category": "accessories",
        "unit_price": "129.90",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-PHN-04",
        "name": "NexaPhone 12 Pro",
        "category": "smartphones",
        "unit_price": "4299.00",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-LTP-04",
        "name": "NexaBook Workstation",
        "category": "laptops",
        "unit_price": "7999.00",
        "final_sale": False,
        "warranty_days": 365,
    },
    {
        "sku": "NX-MON-04",
        "name": "NexaView Ultrawide 34",
        "category": "monitors",
        "unit_price": "2599.00",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-HP-04",
        "name": "NexaSound Studio",
        "category": "headphones",
        "unit_price": "1199.00",
        "final_sale": False,
        "warranty_days": 90,
    },
    {
        "sku": "NX-ACC-05",
        "name": "NexaStand Laptop",
        "category": "accessories",
        "unit_price": "159.90",
        "final_sale": False,
        "warranty_days": 90,
    },
]


def random_person_name(rng: SeededRNG) -> str:
    """Return a Brazilian-style full name."""
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def catalog_slice(count: int) -> list[dict[str, Any]]:
    """Return the first ``count`` product specs, cycling if needed."""
    if count <= len(PRODUCT_SPECS):
        return PRODUCT_SPECS[:count]
    specs = list(PRODUCT_SPECS)
    idx = 0
    while len(specs) < count:
        base = PRODUCT_SPECS[idx % len(PRODUCT_SPECS)]
        extra = dict(base)
        extra["sku"] = f"{base['sku']}-X{len(specs):02d}"
        extra["name"] = f"{base['name']} {len(specs)}"
        specs.append(extra)
        idx += 1
    return specs


def price(value: str | Decimal) -> Decimal:
    """Parse a BRL amount as Decimal."""
    return Decimal(str(value))
