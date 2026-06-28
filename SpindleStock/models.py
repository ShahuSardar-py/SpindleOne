from app.extensions import db
from datetime import datetime

# RAW MATERIAL
class RawMaterial(db.Model):
    __tablename__ = "raw_material"
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(10))  # kg, tons
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    alert_threshold = db.Column(db.Float, default=25)  # user configurable

    # Relationship to lots ordered by inward_date asc
    lots = db.relationship(
        "RawMaterialLot",
        backref="raw_material",
        order_by="RawMaterialLot.inward_date.asc()",
        cascade="all, delete-orphan"
    )

    @property
    def total_quantity(self):
        return sum(lot.remaining_quantity for lot in self.lots if not lot.is_exhausted)

# RAW MATERIAL LOT (Batch)
class RawMaterialLot(db.Model):
    __tablename__ = "raw_material_lot"
    id = db.Column(db.Integer, primary_key=True)
    raw_material_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_material.id"),
        nullable=False
    )
    batch_number = db.Column(db.String(100), unique=True, nullable=False)
    quantity = db.Column(db.Float, nullable=False)  # Original quantity
    remaining_quantity = db.Column(db.Float, nullable=False)  # Quantity left
    price_per_unit = db.Column(db.Float, nullable=False)
    unit_rate = db.Column(db.Float, nullable=True, default=0.0)
    gst_rate = db.Column(db.Float, nullable=True, default=0.0)
    inward_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    is_exhausted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# PRODUCTION BATCH
class Production(db.Model):
    __tablename__ = "production"
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity_produced = db.Column(db.Float)
    expiry_date = db.Column(db.Date)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_raw_material_cost = db.Column(db.Float, default=0.0)

    # relation to materials used
    materials = db.relationship(
        "ProductionMaterial",
        backref="production",
        cascade="all, delete-orphan"
    )

# MATERIAL USED IN PRODUCTION
class ProductionMaterial(db.Model):
    __tablename__ = "production_material"
    id = db.Column(db.Integer, primary_key=True)
    production_id = db.Column(
        db.Integer,
        db.ForeignKey("production.id")
    )
    raw_material_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_material.id")
    )
    quantity_used = db.Column(db.Float)  # stored in kg (matches original behaviour)
    computed_cost = db.Column(db.Float, default=0.0)

    raw_material = db.relationship("RawMaterial")

    lot_consumptions = db.relationship(
        "ProductionLotConsumption",
        backref="production_material",
        cascade="all, delete-orphan"
    )

# PRODUCTION LOT CONSUMPTION (FIFO Audit Trail)
class ProductionLotConsumption(db.Model):
    __tablename__ = "production_lot_consumption"
    id = db.Column(db.Integer, primary_key=True)
    production_material_id = db.Column(
        db.Integer,
        db.ForeignKey("production_material.id"),
        nullable=False
    )
    lot_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_material_lot.id"),
        nullable=False
    )
    quantity_taken = db.Column(db.Float, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)  # quantity_taken * price_per_unit

    lot = db.relationship("RawMaterialLot")

# FINISHED GOODS STOCK
class FinishedStock(db.Model):
    __tablename__ = "finished_stock"

    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100))
    quantity = db.Column(db.Float)
    expiry_date = db.Column(db.Date)
    date = db.Column(db.DateTime, default=datetime.utcnow)

# RECIPE
class Recipe(db.Model):
    __tablename__ = "recipe"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    finished_product_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relation to recipe materials
    materials = db.relationship(
        "RecipeMaterial",
        backref="recipe",
        cascade="all, delete-orphan"
    )

# RECIPE MATERIAL
class RecipeMaterial(db.Model):
    __tablename__ = "recipe_material"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(
        db.Integer,
        db.ForeignKey("recipe.id"),
        nullable=False
    )
    raw_material_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_material.id"),
        nullable=False
    )
    quantity_required = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10), default="kg")

    raw_material = db.relationship("RawMaterial")