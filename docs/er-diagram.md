# Sentinel AI business intelligence ER diagram

```mermaid
erDiagram
    CUSTOMERS ||--o{ SALES_ORDERS : places
    CUSTOMERS ||--o{ SUPPORT_TICKETS : opens
    DEPARTMENTS ||--o{ EMPLOYEES : contains
    EMPLOYEES ||--o{ EMPLOYEES : manages
    EMPLOYEES ||--o{ SALES_ORDERS : owns
    EMPLOYEES ||--o{ SUPPORT_TICKETS : handles
    EMPLOYEES ||--o{ REPORTS : creates
    PRODUCT_CATEGORIES ||--o{ PRODUCTS : classifies
    PRODUCTS ||--o{ PRODUCT_SUPPLIERS : sourced_by
    SUPPLIERS ||--o{ PRODUCT_SUPPLIERS : supplies
    PRODUCTS ||--o{ INVENTORY_STOCK : stocked_as
    WAREHOUSES ||--o{ INVENTORY_STOCK : stores
    INVENTORY_STOCK ||--o{ INVENTORY_MOVEMENTS : records
    SALES_ORDERS ||--|{ SALES_ORDER_ITEMS : contains
    PRODUCTS ||--o{ SALES_ORDER_ITEMS : sold_as
    SALES_ORDERS ||--o{ FINANCE_TRANSACTIONS : originates
    FINANCE_ACCOUNTS ||--o{ FINANCE_TRANSACTIONS : classifies
    PRODUCTS ||--o{ SUPPORT_TICKETS : concerns

    CUSTOMERS {
        uuid id PK
        string customer_number UK
        string company_name
        string industry
        string region
        string status
    }
    PRODUCTS {
        uuid id PK
        string sku UK
        uuid category_id FK
        decimal unit_cost
        decimal unit_price
        int reorder_level
    }
    SALES_ORDERS {
        uuid id PK
        string order_number UK
        uuid customer_id FK
        uuid sales_rep_id FK
        date order_date
        string status
    }
    SALES_ORDER_ITEMS {
        uuid id PK
        uuid sales_order_id FK
        uuid product_id FK
        int quantity
        decimal unit_price
        decimal discount_amount
    }
    INVENTORY_STOCK {
        uuid id PK
        uuid warehouse_id FK
        uuid product_id FK
        int quantity_on_hand
        int quantity_reserved
    }
    EMPLOYEES {
        uuid id PK
        string employee_number UK
        uuid department_id FK
        uuid manager_id FK
        string job_title
        decimal salary
    }
    SUPPLIERS {
        uuid id PK
        string supplier_number UK
        string company_name
        int payment_terms_days
    }
    SUPPORT_TICKETS {
        uuid id PK
        string ticket_number UK
        uuid customer_id FK
        uuid product_id FK
        uuid assigned_employee_id FK
        string priority
        string status
    }
    FINANCE_TRANSACTIONS {
        uuid id PK
        uuid account_id FK
        uuid sales_order_id FK
        date transaction_date
        decimal amount
    }
    REPORTS {
        uuid id PK
        string report_code UK
        uuid created_by_employee_id FK
        string report_type
        string schedule
    }
```

The design is in third normal form: descriptive entities are stored once, many-to-many supplier sourcing is resolved through `product_suppliers`, order headers are separated from line items, inventory balances are unique per product and warehouse, and finance classification is separated from individual transactions.

