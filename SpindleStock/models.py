from app.extensions import db
from datetime import datetime

# RAW MATERIAL 
class RawMaterial(db.Model):
    __tablename__ = "raw_material"
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)  
    amount = db.Column(db.Float)
    unit = db.Column(db.String(10))  # kg,tons
    inward_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
  
# PRODUCTION BATCH 
class Production(db.Model):
    __tablename__ = "production"
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity_produced = db.Column(db.Float)
    expiry_date = db.Column(db.Date)
    date = db.Column(db.DateTime, default=datetime.utcnow)
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
    quantity_used = db.Column(db.Float)
    raw_material = db.relationship("RawMaterial")

# FINISHED GOODS STOCK
class FinishedStock(db.Model):
    __tablename__ = "finished_stock"
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100))
    quantity = db.Column(db.Float)
    expiry_date = db.Column(db.Date)
    date = db.Column(db.DateTime, default=datetime.utcnow)