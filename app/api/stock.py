from datetime import datetime

from flask import jsonify, request
from sqlalchemy import or_

from ..auth import current_user, require
from ..extensions import db
from ..models import CostEntry, Product, StockMovement
from . import bp
from .common import ApiError, apply_fields, get_or_404, paginate

PRODUCT_FIELDS = {"code": "str", "name": "str", "category": "str", "unit": "str", "min_stock": "float",
                  "unit_cost": "float", "storage_location": "str", "supplier_id": "int", "active": "bool"}


@bp.get("/products")
@require("stock.view")
def list_products():
    a = request.args
    q = Product.query.filter(Product.active.is_(True))
    if a.get("q"):
        term = f"%{a['q'].strip()}%"
        q = q.filter(or_(Product.code.ilike(term), Product.name.ilike(term), Product.category.ilike(term)))
    if a.get("category"):
        q = q.filter(Product.category == a["category"])
    items = [p.to_dict() for p in q.order_by(Product.name)]
    if a.get("below") == "1":
        items = [p for p in items if p["below_minimum"]]
    return jsonify(items)


@bp.post("/products")
@require("stock.edit")
def create_product():
    data = request.get_json(silent=True) or {}
    if Product.query.filter_by(code=(data.get("code") or "").strip()).first():
        raise ApiError("Já existe um produto com este código")
    product = apply_fields(Product(quantity=0), data, PRODUCT_FIELDS, required=("code", "name"))
    db.session.add(product)
    initial = float(data.get("quantity") or 0)
    if initial > 0:
        product.quantity = initial
        db.session.add(StockMovement(product=product, kind="entrada", quantity=initial,
                                     unit_cost=product.unit_cost or 0, user=current_user(),
                                     note="Saldo inicial"))
    db.session.commit()
    return jsonify(product.to_dict()), 201


@bp.put("/products/<int:product_id>")
@require("stock.edit")
def update_product(product_id):
    product = get_or_404(Product, product_id, "Produto")
    apply_fields(product, request.get_json(silent=True) or {}, PRODUCT_FIELDS)
    db.session.commit()
    return jsonify(product.to_dict())


@bp.get("/stock/movements")
@require("stock.view")
def list_movements():
    a = request.args
    q = StockMovement.query
    if a.get("product_id"):
        q = q.filter(StockMovement.product_id == int(a["product_id"]))
    if a.get("kind"):
        q = q.filter(StockMovement.kind == a["kind"])
    return jsonify(paginate(q.order_by(StockMovement.created_at.desc()), a))


@bp.post("/stock/movements")
@require("stock.edit")
def create_movement():
    """Entrada (compra), saída avulsa (requisição) ou ajuste de inventário."""
    data = request.get_json(silent=True) or {}
    product = get_or_404(Product, int(data.get("product_id") or 0), "Produto")
    kind = data.get("kind")
    try:
        qty = float(data.get("quantity") or 0)
    except ValueError:
        raise ApiError("Quantidade inválida")
    if kind not in ("entrada", "saida", "ajuste"):
        raise ApiError("Tipo de movimento inválido")
    if kind != "ajuste" and qty <= 0:
        raise ApiError("Quantidade deve ser maior que zero")
    user = current_user()
    unit_cost = float(data.get("unit_cost") or product.unit_cost or 0)
    if kind == "entrada":
        # custo médio ponderado
        total_before = (product.quantity or 0) * (product.unit_cost or 0)
        product.quantity = (product.quantity or 0) + qty
        product.unit_cost = round((total_before + qty * unit_cost) / product.quantity, 4)
    elif kind == "saida":
        if product.quantity < qty:
            raise ApiError(f"Estoque insuficiente (disponível: {product.quantity:g})")
        product.quantity -= qty
        unit_cost = product.unit_cost
    else:  # ajuste: quantidade informada é o novo saldo contado
        if qty < 0:
            raise ApiError("Saldo não pode ser negativo")
        diff = qty - (product.quantity or 0)
        product.quantity = qty
        qty = diff
        unit_cost = product.unit_cost
    mov = StockMovement(product=product, kind=kind, quantity=qty, unit_cost=unit_cost, user=user,
                        supplier_id=int(data["supplier_id"]) if data.get("supplier_id") else None,
                        document=data.get("document"), note=data.get("note"), created_at=datetime.now())
    db.session.add(mov)
    if kind == "saida" and data.get("sector_id"):
        db.session.add(CostEntry(category="Material", amount=round(qty * unit_cost, 2),
                                 description=f"Requisição avulsa: {product.name}",
                                 sector_id=int(data["sector_id"]), created_by_id=user.id))
    db.session.commit()
    return jsonify(mov.to_dict()), 201
