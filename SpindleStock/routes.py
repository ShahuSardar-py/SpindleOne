from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime

from app.extensions import db
from .models import (
    RawMaterial,
    Production,
    FinishedStock,
    ProductionMaterial
)

bp = Blueprint(
    "spindlestock",
    __name__,
    template_folder="templates",
    url_prefix="/stock"
)

# ---------------- DASHBOARD ----------------
@bp.route("/")
def dashboard():

    materials = RawMaterial.query.all()
    productions = Production.query.all()

    total_materials = len(materials)
    total_quantity = sum(m.quantity for m in materials)

    product_data = {}
    for p in productions:
        product_data[p.product_name] = (
            product_data.get(p.product_name, 0)
            + p.quantity_produced
        )

    return render_template(
        "dashboard.html",
        total_materials=total_materials,
        total_quantity=total_quantity,
        product_data=product_data
    )


# ---------------- RAW MATERIAL ----------------
@bp.route("/raw", methods=["GET", "POST"])
def raw_inward():

    if request.method == "POST":

        inward = request.form.get("inward_date")
        expiry = request.form.get("expiry_date")

        inward_date = (
            datetime.strptime(inward, "%Y-%m-%d").date()
            if inward else None
        )

        expiry_date = (
            datetime.strptime(expiry, "%Y-%m-%d").date()
            if expiry else None
        )

        material = RawMaterial(
            name=request.form["name"],
            quantity=float(request.form["quantity"]),
            amount=float(request.form["amount"]),
            unit=request.form["unit"],
            inward_date=inward_date,
            expiry_date=expiry_date
        )

        db.session.add(material)
        db.session.commit()

        return redirect(url_for("spindlestock.raw_inward"))

    materials = RawMaterial.query.all()

    return render_template(
        "raw_inward.html",
        materials=materials
    )


# ---------------- PRODUCTION ----------------
# ---------------- PRODUCTION ----------------
@bp.route("/production", methods=["GET", "POST"])
def production():

    if request.method == "POST":

        product = request.form["product"]
        qty_produced = float(request.form["qty_produced"])
        produced_unit = request.form.get("produced_unit")

        expiry = request.form.get("expiry_date")
        expiry_date = (
            datetime.strptime(expiry, "%Y-%m-%d").date()
            if expiry else None
        )

        # create production batch
        prod = Production(
            product_name=product,
            quantity_produced=qty_produced,
            expiry_date=expiry_date
        )

        db.session.add(prod)
        db.session.flush()

        # materials used
        material_ids = request.form.getlist("material_ids[]")
        quantities_used = request.form.getlist("qty_used[]")
        used_units = request.form.getlist("used_unit[]")

        for mat_id, qty_str, unit in zip(
            material_ids, quantities_used, used_units
        ):
            if not qty_str:
                continue

            qty = float(qty_str)
            material = RawMaterial.query.get(int(mat_id))

            if material and qty > 0:

                # ---- Convert stock to KG ----
                stock_qty = material.quantity
                if material.unit == "ton":
                    stock_qty *= 1000

                # ---- Convert used qty to KG ----
                used_qty = qty
                if unit == "ton":
                    used_qty *= 1000

                # prevent negative stock
                if used_qty > stock_qty:
                    used_qty = stock_qty

                remaining_kg = stock_qty - used_qty

                # ---- Convert back to original unit ----
                if material.unit == "ton":
                    material.quantity = remaining_kg / 1000
                else:
                    material.quantity = remaining_kg

                # store usage
                usage = ProductionMaterial(
                    production_id=prod.id,
                    raw_material_id=material.id,
                    quantity_used=qty
                )

                db.session.add(usage)

        # finished goods entry
        finished = FinishedStock(
            product_name=product,
            quantity=qty_produced,
            expiry_date=expiry_date
        )

        db.session.add(finished)
        db.session.commit()

        return redirect(url_for("spindlestock.production"))

    materials = RawMaterial.query.all()
    productions = Production.query.all()

    return render_template(
        "production.html",
        materials=materials,
        productions=productions
    )
# ---------------- INVENTORY ----------------
@bp.route("/inventory")
def inventory():

    materials = RawMaterial.query.all()
    usages = ProductionMaterial.query.all()

    # total used per material
    used_map = {}
    for u in usages:
        used_map[u.raw_material_id] = (
            used_map.get(u.raw_material_id, 0)
            + u.quantity_used
        )

    inventory_data = []
    for m in materials:
        used_qty = used_map.get(m.id, 0)
        remaining = m.quantity - used_qty

        if remaining < 0:
            remaining = 0

        inventory_data.append({
            "name": m.name,
            "remaining": remaining,
            "unit": m.unit,
            "inward_date": m.inward_date,
            "expiry_date": m.expiry_date
        })

    return render_template(
        "inventory.html",
        materials=inventory_data
    )