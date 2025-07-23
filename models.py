# stockflow-backend/app/models.py

from datetime import datetime
from decimal import Decimal
from app import db # Import the db instance from the app package

# --- Database Models ---

class Company(db.Model):
    __tablename__ = 'companies'
    company_id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    warehouse_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.company_id'), nullable=False)
    warehouse_name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    company = db.relationship('Company', backref='warehouses')

class ProductType(db.Model):
    __tablename__ = 'product_types'
    product_type_id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(100), nullable=False, unique=True)
    default_low_stock_threshold = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class Product(db.Model):
    __tablename__ = 'products'
    # Changed primary key name from 'id' to 'product_id' to match foreign key references
    product_id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(255), nullable=False, unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    product_type_id = db.Column(db.Integer, db.ForeignKey('product_types.product_type_id'))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    product_type = db.relationship('ProductType', backref='products')

class Inventory(db.Model):
    __tablename__ = 'inventory'
    # Composite primary key referencing product_id and warehouse_id
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.warehouse_id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    low_stock_threshold = db.Column(db.Integer) # Per-inventory override for threshold

    product = db.relationship('Product', backref='inventory_records')
    warehouse = db.relationship('Warehouse', backref='inventory_records')

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    supplier_id = db.Column(db.Integer, primary_key=True)
    supplier_name = db.Column(db.String(255), nullable=False)
    contact_person = db.Column(db.String(255))
    contact_email = db.Column(db.String(255))
    phone_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class ProductSupplier(db.Model):
    __tablename__ = 'product_suppliers'
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), primary_key=True)
    supplier = db.relationship('Supplier', backref='product_associations')
    product = db.relationship('Product', backref='supplier_associations')

class SalesActivity(db.Model):
    __tablename__ = 'sales_activity'
    sale_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.warehouse_id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.company_id'), nullable=False)
    quantity_sold = db.Column(db.Integer, nullable=False)
    sale_date = db.Column(db.DateTime, default=datetime.now)

    product = db.relationship('Product', backref='sales')
    warehouse = db.relationship('Warehouse', backref='sales')
    company = db.relationship('Company', backref='sales')

# Note: Bundle and BundleItems models are not used in the API endpoints provided,
# but would be part of a full implementation based on Part 2 schema.
# You can uncomment and include them if you plan to extend the application
# to handle product bundles.
# class Bundle(db.Model):
#     __tablename__ = 'bundles'
#     bundle_id = db.Column(db.Integer, primary_key=True)
#     bundle_name = db.Column(db.String(255), nullable=False)
#     sku = db.Column(db.String(255), nullable=False, unique=True)
#     description = db.Column(db.Text)
#     price = db.Column(db.Numeric(10, 2))
#     created_at = db.Column(db.DateTime, default=datetime.now)
#     updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

# class BundleItem(db.Model):
#     __tablename__ = 'bundle_items'
#     bundle_item_id = db.Column(db.Integer, primary_key=True)
#     bundle_id = db.Column(db.Integer, db.ForeignKey('bundles.bundle_id'), nullable=False)
#     product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
#     quantity = db.Column(db.Integer, nullable=False)
#     bundle = db.relationship('Bundle', backref='bundle_items')
#     product = db.relationship('Product', backref='bundle_of')
#     __table_args__ = (db.UniqueConstraint('bundle_id', 'product_id', name='_bundle_product_uc'),)

