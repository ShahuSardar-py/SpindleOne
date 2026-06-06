from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta

from app.extensions import db
from .models import (
    RawMaterial,
    RawMaterialLot,
    Production,
    FinishedStock,
    ProductionMaterial,
    ProductionLotConsumption,
    Recipe,
    RecipeMaterial
)

bp = Blueprint(
    "spindlestock",
    __name__,
    template_folder="templates",
    url_prefix="/stock"
)

# ==============================
# FIFO STOCK CONSUMPTION UTILITY
# ==============================
def consume_fifo(raw_material_id, quantity_needed):
    """
    Drains the oldest active lots first (FIFO).
    Marks is_exhausted=True when remaining_quantity reaches 0.
    Returns: list of ProductionLotConsumption objects + total cost.
    """
    # Fetch active lots ordered by inward_date asc
    lots = RawMaterialLot.query.filter_by(
        raw_material_id=raw_material_id,
        is_exhausted=False
    ).order_by(RawMaterialLot.inward_date.asc()).all()

    consumptions = []
    total_cost = 0.0
    remaining_needed = quantity_needed

    for lot in lots:
        if remaining_needed <= 0:
            break
        
        avail = lot.remaining_quantity
        if avail <= 0:
            continue
            
        taken = min(remaining_needed, avail)
        lot.remaining_quantity -= taken
        
        # Check if lot is exhausted (handling float precision)
        if lot.remaining_quantity <= 1e-6:
            lot.remaining_quantity = 0.0
            lot.is_exhausted = True
            
        cost = taken * lot.price_per_unit
        total_cost += cost
        remaining_needed -= taken

        consumption = ProductionLotConsumption(
            lot_id=lot.id,
            quantity_taken=taken,
            price_per_unit=lot.price_per_unit,
            cost=cost
        )
        consumptions.append(consumption)

    if remaining_needed > 1e-6:
        raise ValueError("Not enough stock in non-exhausted lots to fulfill request.")

    return consumptions, total_cost


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
        if m.alert_threshold and m.total_quantity <= m.alert_threshold:
            low_stock.append(m)

    # EXPIRING SOON MATERIALS (within 7 days)
    today = datetime.utcnow().date()
    expiring_materials = []

    # Check active lots for expiration dates within 7 days
    active_lots = RawMaterialLot.query.filter_by(is_exhausted=False).all()
    for lot in active_lots:
        if lot.expiry_date:
            if lot.expiry_date <= today + timedelta(days=7):
                expiring_materials.append(lot)

    expiring_count = len(expiring_materials)

    return render_template(
        "dashboardStock.html",
        total_materials=total_materials,
        product_data=product_data,
        low_stock=low_stock,
        expiring_materials=expiring_materials,
        expiring_count=expiring_count
    )


# ==============================
# RAW MATERIAL LOTS REGISTRY
# ==============================
@bp.route("/raw", methods=["GET", "POST"])
def raw_inward():
    if request.method == "POST":
        name = request.form["name"].strip()
        qty = float(request.form["quantity"])
        amount = float(request.form["amount"])
        unit = request.form["unit"]
        inward = request.form.get("inward_date")
        expiry = request.form.get("expiry_date")
        batch_number = request.form.get("batch_number", "").strip()

        inward_date = (
            datetime.strptime(inward, "%Y-%m-%d").date()
            if inward else datetime.utcnow().date()
        )

        expiry_date = (
            datetime.strptime(expiry, "%Y-%m-%d").date()
            if expiry else None
        )

        # 1. Handle RawMaterial creation or retrieval
        material = RawMaterial.query.filter_by(name=name).first()
        if not material:
            material = RawMaterial(
                name=name,
                unit=unit
            )
            db.session.add(material)
            db.session.flush()

        # 2. Handle unique batch_number generation if empty
        if not batch_number:
            batch_number = f"LOT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{material.id}"
        
        # Check uniqueness of batch_number
        existing_lot = RawMaterialLot.query.filter_by(batch_number=batch_number).first()
        if existing_lot:
            flash(f"Batch number '{batch_number}' already exists. Please choose a unique batch number.")
            materials = RawMaterial.query.all()
            lots = RawMaterialLot.query.order_by(RawMaterialLot.inward_date.desc()).all()
            return render_template("raw_inward.html", materials=materials, lots=lots)

        # 3. Calculate price_per_unit
        price_per_unit = amount / qty if qty > 0 else 0.0

        # 4. Add RawMaterialLot
        lot = RawMaterialLot(
            raw_material_id=material.id,
            batch_number=batch_number,
            quantity=qty,
            remaining_quantity=qty,
            price_per_unit=price_per_unit,
            inward_date=inward_date,
            expiry_date=expiry_date
        )
        db.session.add(lot)
        db.session.commit()

        flash(f"Successfully recorded lot '{batch_number}' for {name}!")
        return redirect(url_for("spindlestock.raw_inward"))

    materials = RawMaterial.query.all()
    lots = RawMaterialLot.query.order_by(RawMaterialLot.inward_date.desc()).all()

    return render_template(
        "raw_inward.html",
        materials=materials,
        lots=lots
    )


# ==============================
# PRODUCTION ENTRY
# ==============================
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
            expiry_date=expiry_date,
            total_raw_material_cost=0.0
        )
        db.session.add(prod)
        db.session.flush()

        material_ids = request.form.getlist("material_ids[]")
        quantities_used = request.form.getlist("qty_used[]")
        used_units = request.form.getlist("used_unit[]")

        total_production_cost = 0.0

        for mat_id, qty_str, unit in zip(
            material_ids, quantities_used, used_units
        ):
            if not qty_str:
                continue

            qty = float(qty_str)
            material = RawMaterial.query.get(int(mat_id))

            if material and qty > 0:
                # Convert usage to KG for validation
                used_kg = qty * 1000 if unit == "ton" else qty

                # Convert stock (total quantity across lots) to KG for validation
                stock_kg = (
                    material.total_quantity * 1000
                    if material.unit == "ton"
                    else material.total_quantity
                )

                # 🚨 STOCK CHECK
                if used_kg > stock_kg:
                    flash(
                        f"Not enough {material.name} in stock. "
                        f"Available: {stock_kg} kg only."
                    )
                    db.session.rollback()
                    return redirect(url_for("spindlestock.production"))

                # Convert target usage quantity back to raw material's base unit to pass to FIFO drain
                qty_needed_in_raw_unit = used_kg / 1000 if material.unit == "ton" else used_kg

                # Drain stock using consume_fifo
                consumptions, material_cost = consume_fifo(material.id, qty_needed_in_raw_unit)

                # Log ProductionMaterial line
                usage = ProductionMaterial(
                    production_id=prod.id,
                    raw_material_id=material.id,
                    quantity_used=used_kg, # in KG
                    computed_cost=material_cost
                )
                db.session.add(usage)
                db.session.flush()

                # Link consumptions to production_material line
                for consumption in consumptions:
                    consumption.production_material_id = usage.id
                    db.session.add(consumption)

                total_production_cost += material_cost

        # Save finished stock
        finished = FinishedStock(
            product_name=product,
            quantity=qty_produced,
            expiry_date=expiry_date
        )
        db.session.add(finished)

        # Update total cost of production batch
        prod.total_raw_material_cost = total_production_cost
        db.session.commit()

        flash(f"{product} production saved successfully! Total Material Cost: ₹{total_production_cost:.2f}")
        return redirect(url_for("spindlestock.production"))

    materials = RawMaterial.query.all()
    productions = Production.query.all()
    recipes = Recipe.query.all()

    return render_template(
        "production.html",
        materials=materials,
        productions=productions,
        recipes=recipes
    )


# ==============================
# STOCK BALANCE
# ==============================
@bp.route("/inventory")
def inventory():
    materials = RawMaterial.query.all()
    inventory_data = []

    for m in materials:
        # Determine earliest active inward and expiry dates for display in table
        active_lots = [lot for lot in m.lots if not lot.is_exhausted]
        inward_date = active_lots[0].inward_date if active_lots else None
        expiry_date = active_lots[0].expiry_date if active_lots else None

        inventory_data.append({
            "name": m.name,
            "remaining": m.total_quantity,
            "unit": m.unit,
            "inward_date": inward_date,
            "expiry_date": expiry_date
        })

    return render_template(
        "inventory.html",
        materials=inventory_data
    )


# ==============================
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


# ==============================
# RECIPES MANAGEMENT
# ==============================
@bp.route("/recipes")
def recipes():
    all_recipes = Recipe.query.all()
    return render_template("recipes.html", recipes=all_recipes)


@bp.route("/recipes/create", methods=["GET", "POST"])
def create_recipe():
    if request.method == "POST":
        name = request.form["name"]
        finished_product_name = request.form.get("finished_product_name")

        existing = Recipe.query.filter_by(name=name).first()
        if existing:
            flash(f"A recipe named '{name}' already exists.")
            materials = RawMaterial.query.all()
            return render_template("create_recipe.html", materials=materials)

        recipe = Recipe(
            name=name,
            finished_product_name=finished_product_name
        )
        db.session.add(recipe)
        db.session.flush()

        raw_mat_ids = request.form.getlist("raw_material_ids[]")
        qty_reqs = request.form.getlist("qty_required[]")
        units = request.form.getlist("units[]")

        for rm_id, qty_str, r_unit in zip(raw_mat_ids, qty_reqs, units):
            if not rm_id or not qty_str:
                continue
            qty = float(qty_str)
            rm = RecipeMaterial(
                recipe_id=recipe.id,
                raw_material_id=int(rm_id),
                quantity_required=qty,
                unit=r_unit
            )
            db.session.add(rm)

        db.session.commit()
        flash(f"Recipe '{name}' created successfully!")
        return redirect(url_for("spindlestock.recipes"))

    materials = RawMaterial.query.all()
    return render_template("create_recipe.html", materials=materials)


@bp.route("/recipes/<int:recipe_id>/edit", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    if request.method == "POST":
        name = request.form["name"]
        finished_product_name = request.form.get("finished_product_name")

        if name != recipe.name:
            existing = Recipe.query.filter_by(name=name).first()
            if existing:
                flash(f"A recipe named '{name}' already exists.")
                materials = RawMaterial.query.all()
                return render_template("create_recipe.html", recipe=recipe, materials=materials)

        recipe.name = name
        recipe.finished_product_name = finished_product_name

        RecipeMaterial.query.filter_by(recipe_id=recipe.id).delete()

        raw_mat_ids = request.form.getlist("raw_material_ids[]")
        qty_reqs = request.form.getlist("qty_required[]")
        units = request.form.getlist("units[]")

        for rm_id, qty_str, r_unit in zip(raw_mat_ids, qty_reqs, units):
            if not rm_id or not qty_str:
                continue
            qty = float(qty_str)
            rm = RecipeMaterial(
                recipe_id=recipe.id,
                raw_material_id=int(rm_id),
                quantity_required=qty,
                unit=r_unit
            )
            db.session.add(rm)

        db.session.commit()
        flash(f"Recipe '{name}' updated successfully!")
        return redirect(url_for("spindlestock.recipes"))

    materials = RawMaterial.query.all()
    return render_template("create_recipe.html", recipe=recipe, materials=materials)


@bp.route("/recipes/<int:recipe_id>/delete", methods=["POST"])
def delete_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    name = recipe.name
    db.session.delete(recipe)
    db.session.commit()
    flash(f"Recipe '{name}' deleted successfully!")
    return redirect(url_for("spindlestock.recipes"))


@bp.route("/recipes/<int:recipe_id>/json")
def recipe_json(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    materials_list = []
    for rm in recipe.materials:
        materials_list.append({
            "raw_material_id": rm.raw_material_id,
            "raw_material_name": rm.raw_material.name if rm.raw_material else "Unknown",
            "quantity": rm.quantity_required,
            "unit": rm.unit
        })
    return {
        "id": recipe.id,
        "name": recipe.name,
        "finished_product_name": recipe.finished_product_name or "",
        "materials": materials_list
    }