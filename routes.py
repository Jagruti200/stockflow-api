# stockflow-backend/app/routes.py

from flask import Blueprint, request, jsonify, current_app # Import Blueprint
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import func, distinct
from datetime import datetime, timedelta
from decimal import Decimal

# Import db and models from the app package
from app import db
from app.models import Company, Warehouse, ProductType, Product, Inventory, Supplier, ProductSupplier, SalesActivity

# Create a Blueprint instance
# The name 'api_bp' is arbitrary but descriptive.
# The url_prefix will apply to all routes defined in this blueprint.
api_bp = Blueprint('api_bp', __name__, url_prefix='/api')


@api_bp.route('/products', methods=['POST']) # Use api_bp.route
def create_product():
    """
    API endpoint to create a new product and its initial inventory.
    Handles input validation, SKU uniqueness, and atomic database operations.
    """
    data = request.json

    # 1. Input Validation and Error Handling
    if not data:
        return jsonify({"message": "Invalid JSON data"}), 400

    required_fields = ['name', 'sku', 'price', 'warehouse_id', 'initial_quantity']
    for field in required_fields:
        if field not in data:
            return jsonify({"message": f"Missing required field: {field}"}), 400

    try:
        # Validate data types and values
        name = data['name']
        sku = data['sku']
        # Ensure price is a Decimal for precision with monetary values
        price = Decimal(str(data['price']))
        warehouse_id = int(data['warehouse_id']) # Ensure warehouse_id is an integer
        initial_quantity = int(data['initial_quantity']) # Ensure quantity is an integer

        if price < 0:
            return jsonify({"message": "Price cannot be negative"}), 400
        if initial_quantity < 0:
            return jsonify({"message": "Initial quantity cannot be negative"}), 400

        # Check if warehouse exists
        warehouse = Warehouse.query.get(warehouse_id)
        if not warehouse:
            return jsonify({"message": f"Warehouse with ID {warehouse_id} not found"}), 404

        # 2. Check SKU uniqueness before attempting to create product
        existing_product = Product.query.filter_by(sku=sku).first()
        if existing_product:
            return jsonify({"message": f"Product with SKU '{sku}' already exists."}), 409 # 409 Conflict

        # Start a transaction for atomicity
        db.session.begin_nested() # Use nested transaction for better rollback control

        # Create new product
        product = Product(
            product_name=name, # <--- FIX: Changed 'name' to 'product_name' to match the model
            sku=sku,
            price=price
            # No warehouse_id here, it's handled by Inventory
        )
        db.session.add(product)
        # Flush to get product.id before committing, necessary for new objects
        db.session.flush()

        # Update or create inventory count
        # Check if inventory for this product in this warehouse already exists
        inventory = Inventory.query.filter_by(
            product_id=product.product_id, # Use product.product_id here
            warehouse_id=warehouse_id
        ).first()

        if inventory:
            # If product already exists in this warehouse, update quantity
            inventory.quantity += initial_quantity
        else:
            # Otherwise, create a new inventory record
            inventory = Inventory(
                product_id=product.product_id, # Use product.product_id here
                warehouse_id=warehouse_id,
                quantity=initial_quantity
            )
            db.session.add(inventory)

        db.session.commit() # Commit both product and inventory in a single transaction

        return jsonify({"message": "Product created successfully", "product_id": product.product_id}), 201 # 201 Created

    except ValueError as e:
        db.session.rollback() # Rollback if type conversion fails
        return jsonify({"message": f"Invalid data type or value: {e}"}), 400
    except IntegrityError as e:
        db.session.rollback() # Rollback on database constraint errors
        # This catch might be redundant after explicit SKU check, but good for other constraints
        # e.orig provides the underlying database error, which might have more detail
        error_message = str(e.orig) if e.orig else str(e)
        current_app.logger.error(f"Database integrity error: {error_message}", exc_info=True)
        return jsonify({"message": f"Database integrity error: {error_message}"}), 400
    except OperationalError as e:
        db.session.rollback() # Rollback on database operational errors (e.g., connection)
        current_app.logger.error(f"Database operational error: {e}", exc_info=True)
        return jsonify({"message": f"Database operational error: {e}"}), 500
    except Exception as e:
        db.session.rollback() # Catch any other unexpected errors
        current_app.logger.error(f"An unexpected error occurred during product creation: {e}", exc_info=True) # Log the error
        return jsonify({"message": "An unexpected error occurred"}), 500


@api_bp.route('/companies/<int:company_id>/alerts/low-stock', methods=['GET']) # Use api_bp.route
def get_low_stock_alerts(company_id):
    """
    Returns low-stock alerts for a specific company.

    Business Rules Applied:
    - Low stock threshold varies by product type (default_low_stock_threshold).
    - Threshold can be overridden per product-warehouse combination (Inventory.low_stock_threshold).
    - Only alert for products with recent sales activity (last 30 days).
    - Must handle multiple warehouses per company.
    - Include supplier information for reordering.
    - days_until_stockout is calculated based on average daily sales in the recent period.
    """
    try:
        # 1. Validate company_id
        company = Company.query.get(company_id)
        if not company:
            return jsonify({"message": f"Company with ID {company_id} not found"}), 404

        alerts = []
        # Define the window for "recent sales activity" (e.g., last 30 days)
        # This can be made configurable via query parameters in a real application.
        thirty_days_ago = datetime.now() - timedelta(days=30)

        # Query for all inventory items associated with the company's warehouses
        # Join Inventory with Product, ProductType, Warehouse
        # Filter by company_id through warehouses
        inventory_items = db.session.query(
            Inventory, Product, ProductType, Warehouse
        ).join(
            Product, Inventory.product_id == Product.product_id
        ).join(
            Warehouse, Inventory.warehouse_id == Warehouse.warehouse_id
        ).outerjoin( # Use outerjoin for ProductType as it might be NULL if ON DELETE SET NULL was triggered
            ProductType, Product.product_type_id == ProductType.product_type_id
        ).filter(
            Warehouse.company_id == company_id
        ).all()

        for inventory, product, product_type, warehouse in inventory_items:
            # Determine effective low stock threshold
            # Priority: Inventory override > ProductType default > Global fallback (10)
            threshold = inventory.low_stock_threshold
            if threshold is None: # If no specific override, check product type
                if product_type:
                    threshold = product_type.default_low_stock_threshold
                else:
                    threshold = 10 # Fallback if no product type or override is set

            # Ensure threshold is an integer (should be by schema, but defensive check)
            if not isinstance(threshold, int):
                threshold = 10 # Default if it somehow ends up non-integer

            # Check if current stock is below the threshold
            if inventory.quantity <= threshold:
                # Check for recent sales activity for this specific product in this warehouse
                # Sum quantity_sold for the product in the specific warehouse within the last 30 days
                recent_sales_sum = db.session.query(func.sum(SalesActivity.quantity_sold)).filter(
                    SalesActivity.product_id == product.product_id,
                    SalesActivity.warehouse_id == warehouse.warehouse_id,
                    SalesActivity.sale_date >= thirty_days_ago
                ).scalar() or 0 # Use .scalar() to get the single sum value, default to 0 if no sales

                # Only alert if there's recent sales activity (sum of sales > 0)
                if recent_sales_sum > 0:
                    # Calculate days until stockout
                    days_until_stockout = None
                    # Find the earliest sale date within the 30-day window to calculate actual days tracked
                    earliest_recent_sale_date = db.session.query(func.min(SalesActivity.sale_date)).filter(
                        SalesActivity.product_id == product.product_id,
                        SalesActivity.warehouse_id == warehouse.warehouse_id,
                        SalesActivity.sale_date >= thirty_days_ago
                    ).scalar()

                    # Calculate the number of days over which sales occurred
                    # Use max(1, ...) to prevent division by zero if all sales happened on the same day
                    if earliest_recent_sale_date:
                        num_days_sales_tracked = (datetime.now() - earliest_recent_sale_date).days
                        if num_days_sales_tracked == 0: # Handle case where all sales are exactly today
                            num_days_sales_tracked = 1
                    else:
                        num_days_sales_tracked = 1 # Fallback if no sales date found (shouldn't happen if recent_sales_sum > 0)

                    average_daily_sales = recent_sales_sum / max(1, num_days_sales_tracked)

                    if average_daily_sales > 0:
                        days_until_stockout = round(inventory.quantity / average_daily_sales)

                    # Get supplier information for the product
                    suppliers_data = []
                    # Join ProductSupplier with Supplier to get supplier details
                    product_suppliers = db.session.query(ProductSupplier, Supplier).join(
                        Supplier, ProductSupplier.supplier_id == Supplier.supplier_id
                    ).filter(
                        ProductSupplier.product_id == product.product_id
                    ).all()

                    for ps, supplier in product_suppliers:
                        suppliers_data.append({
                            "id": supplier.supplier_id,
                            "name": supplier.supplier_name,
                            "contact_email": supplier.contact_email
                        })

                    alerts.append({
                        "product_id": product.product_id,
                        "product_name": product.product_name,
                        "sku": product.sku,
                        "warehouse_id": warehouse.warehouse_id,
                        "warehouse_name": warehouse.warehouse_name,
                        "current_stock": inventory.quantity,
                        "threshold": threshold,
                        "days_until_stockout": days_until_stockout,
                        "supplier": suppliers_data # This will be a list of supplier objects
                    })

        return jsonify({
            "alerts": alerts,
            "total_alerts": len(alerts)
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching low stock alerts for company {company_id}: {e}", exc_info=True)
        return jsonify({"message": "An unexpected error occurred while fetching alerts"}), 500
