import os
from pymongo import MongoClient
from dotenv import load_dotenv
from .schema import extract_schema
from functools import lru_cache

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

# ── Collection References
banking_collection = db["bank_accounts"]
client_collection = db["tenants"]
invoice_collection = db["rent_invoices"]

service_collection = db["properties"]
users_collection = db["users"]
vendor_collection = db["maintenance_vendors"]
transaction_collection = db["transactions"]



# ── Allowed collections (whitelist for security)
ALLOWED_COLLECTIONS = {
    "bank_accounts": banking_collection,
    "tenants": client_collection,
    "rent_invoices": invoice_collection,
    "properties": service_collection,
    "users": users_collection,
    "maintenance_vendors": vendor_collection,
    "transactions": transaction_collection,
}

#Explicitly Blocked Fields

BLOCKED_FIELDS = {
    "users": ["password", "isFirstLogin", "isVerified", "profilePhoto", "createdAt", "updatedAt", "__v"],
    "bank_accounts": ["accountNumber", "ifscCode"],
    "tenants": ["companyLogo", "gstNumber", "panNumber", "createdAt", "updatedAt", "__v", "phoneNumber"],
    "maintenance_vendors": ["internal_notes"],
    "rent_invoices": ["discountPercentage"],
    "properties": ["deletedAt", "createdAt", "updatedAt", "__v"],
    "transactions": [],
}

#Dynamically Allowed Fields
@lru_cache(maxsize=1)
def get_allowed_fields():
    """
    Dynamically extract schema from MongoDB,
    restrict to allowed collections,
    remove blocked fields.
    Cached for performance.
    """
    raw_schema= extract_schema()

    allowed = {}
    for collection in ALLOWED_COLLECTIONS.keys():
        fields = list(
            raw_schema.get(collection,{}).get("fields",{}).keys()
            )
        blocked = BLOCKED_FIELDS.get(collection,[])

        # Remove blocked fields
        secure_fields= [f for f in fields if f not in blocked]

        allowed[collection] = secure_fields
    
    return allowed
    


'''# ── Allowed fields per collection (security layer)
ALLOWED_FIELDS = {
    "invoices": [
        "invoice_number", "client_name", "total", "status",
        "issue_date", "due_date", "services",
    ],
    "clients": [
        "client_name", "email", "phone", "address",
        "status", "created_at",
    ],
    "vendors": [
        "vendor_name", "email", "phone", "status",
        "total_paid", "total_pending", "created_at",
    ],
    "services": [
        "service_name", "description", "price",
        "usage_count", "status",
    ],
    "banking": [
        "account_name", "bank_name", "account_number",
        "balance", "account_type",
    ],
    "transactions": [
        "transaction_id", "account_name", "type",
        "amount", "date", "description",
    ],
    "Users": [
        "Name","Location"
    ]
}
'''