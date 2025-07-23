# stockflow-backend/run.py

from app import create_app, db
# Import models here to ensure they are available for db.create_all()
from app.models import Company, Warehouse, ProductType, Product, Inventory, Supplier, ProductSupplier, SalesActivity
from datetime import datetime, timedelta
from decimal import Decimal

app = create_app()

# This block will run when you execute run.py directly.
# It creates the database tables and seeds initial data for testing.
with app.app_context():
    db.create_all() # Create all tables defined in models.py

    # Seed Data (for testing the endpoint) - Only runs if tables are empty
    if not Company.query.first():
        print("Seeding initial data...")
        company1 = Company(company_name="Acme Corp")
        company2 = Company(company_name="Widgets Inc")
        db.session.add_all([company1, company2])
        db.session.commit()

        warehouse1 = Warehouse(company_id=company1.company_id, warehouse_name="Main Warehouse A", location="123 Main St")
        warehouse2 = Warehouse(company_id=company1.company_id, warehouse_name="West Coast Depot", location="456 Elm St")
        warehouse3 = Warehouse(company_id=company2.company_id, warehouse_name="Widgets HQ Warehouse", location="789 Pine Ave")
        db.session.add_all([warehouse1, warehouse2, warehouse3])
        db.session.commit()

        pt_general = ProductType(type_name="General Goods", default_low_stock_threshold=10)
        pt_critical = ProductType(type_name="Critical Components", default_low_stock_threshold=5)
        db.session.add_all([pt_general, pt_critical])
        db.session.commit()

        product_a = Product(product_name="Widget A", sku="WID-001", price=Decimal('10.50'), product_type=pt_general)
        product_b = Product(product_name="Gadget B", sku="GAD-002", price=Decimal('25.00'), product_type=pt_critical)
        product_c = Product(product_name="Doohickey C", sku="DOO-003", price=Decimal('5.00'), product_type=pt_general)
        product_d = Product(product_name="Critical Part X", sku="CPX-004", price=Decimal('100.00'), product_type=pt_critical)
        db.session.add_all([product_a, product_b, product_c, product_d])
        db.session.commit()

        supplier1 = Supplier(supplier_name="Supplier Corp", contact_email="orders@supplier.com")
        supplier2 = Supplier(supplier_name="Parts R Us", contact_email="sales@partsrus.com")
        db.session.add_all([supplier1, supplier2])
        db.session.commit()

        # Product-Supplier relationships
        db.session.add(ProductSupplier(product=product_a, supplier=supplier1))
        db.session.add(ProductSupplier(product=product_b, supplier=supplier1))
        db.session.add(ProductSupplier(product=product_a, supplier=supplier2)) # Product A has two suppliers
        db.session.add(ProductSupplier(product=product_d, supplier=supplier2))
        db.session.commit()

        # Inventory records
        # Product A in Warehouse 1 (low stock, threshold 20, current 5)
        db.session.add(Inventory(product=product_a, warehouse=warehouse1, quantity=5, low_stock_threshold=20))
        # Product A in Warehouse 2 (sufficient stock)
        db.session.add(Inventory(product=product_a, warehouse=warehouse2, quantity=50))
        # Product B in Warehouse 1 (sufficient stock)
        db.session.add(Inventory(product=product_b, warehouse=warehouse1, quantity=30))
        # Product B in Warehouse 3 (Widgets Inc, very low stock, threshold 10, current 2)
        db.session.add(Inventory(product=product_b, warehouse=warehouse3, quantity=2, low_stock_threshold=10))
        # Product D in Warehouse 1 (low stock, threshold 5, current 3, but NO RECENT SALES)
        db.session.add(Inventory(product=product_d, warehouse=warehouse1, quantity=3, low_stock_threshold=5))
        # Product C in Warehouse 1 (sufficient stock, no specific threshold override)
        db.session.add(Inventory(product=product_c, warehouse=warehouse1, quantity=100))
        db.session.commit()

        # Sales Activity (for last 30 days)
        today = datetime.now()
        # Sales for Product A in Warehouse 1 (recent sales)
        db.session.add(SalesActivity(product=product_a, warehouse=warehouse1, company=company1, quantity_sold=2, sale_date=today - timedelta(days=5)))
        db.session.add(SalesActivity(product=product_a, warehouse=warehouse1, company=company1, quantity_sold=3, sale_date=today - timedelta(days=15)))
        # Sales for Product B in Warehouse 3 (recent sales)
        db.session.add(SalesActivity(product=product_b, warehouse=warehouse3, company=company2, quantity_sold=5, sale_date=today - timedelta(days=10)))
        db.session.add(SalesActivity(product=product_b, warehouse=warehouse3, company=company2, quantity_sold=3, sale_date=today - timedelta(days=20)))
        # Old sales for Product D in Warehouse 1 (not recent, shouldn't trigger alert based on sales activity)
        db.session.add(SalesActivity(product=product_d, warehouse=warehouse1, company=company1, quantity_sold=1, sale_date=today - timedelta(days=60)))
        db.session.commit()
        print("Data seeding complete.")
    else:
        print("Database already contains data, skipping seeding.")

if __name__ == '__main__':
    # Run the Flask development server
    app.run(debug=True) # Set debug=False in production for security and performance