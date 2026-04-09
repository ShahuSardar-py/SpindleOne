from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash

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

# DASHBOARD
from datetime import datetime, timedelta

# ==============================
# DASHBOARD
# ==============================
@bp.route("/")
def dashboard():

    materials = RawMaterial.query.all()
    productions = Production.query.all()

    # KPI 1
    total_materials = len(materials)

    # Production chart
    product_data = {}
    for p in productions:
        product_data[p.product_name] = (
            product_data.get(p.product_name, 0)
            + p.quantity_produced
        )

    # LOW STOCK ALERTS
    low_stock = []
    for m in materials:
        if m.alert_threshold and m.quantity <= m.alert_threshold:
            low_stock.append(m)

    # EXPIRING SOON MATERIALS (within 7 days)
    today = datetime.now().date()
    expiring_materials = []

    for m in materials:
        if m.expiry_date:
            if m.expiry_date <= today + timedelta(days=7):
                expiring_materials.append(m)

    expiring_count = len(expiring_materials)

    return render_template(
        "dashboardStock.html",
        total_materials=total_materials,
        product_data=product_data,
        low_stock=low_stock,
        expiring_materials=expiring_materials,
        expiring_count=expiring_count
    )
# RAW MATERIAL
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



@bp.route("/production", methods=["GET", "POST"])
def production():

    if request.method == "POST":

        product = request.form["product"]
        qty_produced = float(request.form["qty_produced"])

        expiry = request.form.get("expiry_date")
        expiry_date = (
            datetime.strptime(expiry, "%Y-%m-%d").date()
            if expiry else None
        )

        prod = Production(
            product_name=product,
            quantity_produced=qty_produced,
            expiry_date=expiry_date
        )

        db.session.add(prod)
        db.session.flush()

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

                # Convert usage to KG
                used_kg = qty * 1000 if unit == "ton" else qty

                # Convert stock to KG
                stock_kg = (
                    material.quantity * 1000
                    if material.unit == "ton"
                    else material.quantity
                )

                # 🚨 STOCK CHECK
                if used_kg > stock_kg:
                    flash(
                        f"Not enough {material.name} in stock. "
                        f"Available: {stock_kg} kg only."
                    )
                    db.session.rollback()
                    return redirect(url_for("spindlestock.production"))

                # subtract stock
                remaining_kg = stock_kg - used_kg

                # store back in original unit
                if material.unit == "ton":
                    material.quantity = remaining_kg / 1000
                else:
                    material.quantity = remaining_kg

                usage = ProductionMaterial(
                    production_id=prod.id,
                    raw_material_id=material.id,
                    quantity_used=used_kg
                )

                db.session.add(usage)

        finished = FinishedStock(
            product_name=product,
            quantity=qty_produced,
            expiry_date=expiry_date
        )

        db.session.add(finished)
        db.session.commit()

        flash(f"{product} production saved successfully!")
        return redirect(url_for("spindlestock.production"))

    materials = RawMaterial.query.all()
    productions = Production.query.all()

    return render_template(
        "production.html",
        materials=materials,
        productions=productions
    )
@bp.route("/inventory")
def inventory():

    materials = RawMaterial.query.all()

    inventory_data = [] 
    

    for m in materials:
        inventory_data.append({
            "name": m.name,
            "remaining": m.quantity,
            "unit": m.unit,
            "inward_date": m.inward_date,
            "expiry_date": m.expiry_date
        })

    return render_template(
        "inventory.html",
        materials=inventory_data
    )

# EDIT ALERTS
# ==============================
@bp.route("/edit_alerts", methods=["GET", "POST"])
def edit_alerts():

    materials = RawMaterial.query.all()

    if request.method == "POST":

        material_id = request.form["material_id"]
        quantity = float(request.form["alert_quantity"])
        unit = request.form["unit"]

        material = RawMaterial.query.get(material_id)

        if unit == "ton":
            quantity = quantity * 1000

        material.alert_threshold = quantity
        db.session.commit()

        flash("Alert updated!")
        return redirect(url_for("spindlestock.dashboard"))

    return render_template(
        "edit_alerts.html",
        materials=materials
    )