import random
from datetime import datetime, timedelta
from .database import (
    invoice_collection,
    client_collection,
    vendor_collection,
    service_collection,
    banking_collection,
    transaction_collection,
)

# ── Static Reference Data ──────────────────────────────────────────

CLIENTS = [
    {"client_name": "Sarah Jenkins - Apt 1204", "email": "sarah.j@marina-towers.ae", "phone": "+971-50-123-4567", "address": "Marina Heights, Dubai", "status": "active"},
    {"client_name": "Khalid Mansoor - Villa 8", "email": "khalid.m@palm.ae", "phone": "+971-50-987-6543", "address": "Palm Jumeirah, Dubai", "status": "active"},
    {"client_name": "TechHub Offices LLC", "email": "billing@techhub.ae", "phone": "+971-4-555-0199", "address": "Business Bay, Dubai", "status": "active"},
    {"client_name": "Elena Rossi - Apt 305", "email": "elena.r@downtown-res.ae", "phone": "+971-55-222-3344", "address": "Downtown Dubai", "status": "active"},
    {"client_name": "Green Earth Properties", "email": "hq@greenearth.ae", "phone": "+971-4-888-7766", "address": "JVC, Dubai", "status": "active"},
    {"client_name": "James Wilson - Penthouse", "email": "james.w@skyline.ae", "phone": "+971-58-111-2222", "address": "JBR, Dubai", "status": "inactive"},
]

VENDORS = [
    {"vendor_name": "Elite Facilities Mgmt", "email": "service@elite-fm.ae", "phone": "+971-4-444-1111", "status": "active", "total_paid": 45000, "total_pending": 12000},
    {"vendor_name": "DEWA (Utilities)", "email": "customercare@dewa.gov.ae", "phone": "991", "status": "active", "total_paid": 125000, "total_pending": 8500},
    {"vendor_name": "Dubai Security Systems", "email": "ops@dubaisecurity.ae", "phone": "+971-4-333-2222", "status": "active", "total_paid": 32000, "total_pending": 0},
    {"vendor_name": "Landscaping Pros", "email": "garden@landpros.ae", "phone": "+971-52-444-5555", "status": "inactive", "total_paid": 5000, "total_pending": 1500},
    {"vendor_name": "Elevator Tech LLC", "email": "maint@elevate.ae", "phone": "+971-4-222-3333", "status": "active", "total_paid": 18000, "total_pending": 4000},
]

SERVICES = [
    {"service_name": "Studio Apt - High Floor", "description": "Fully furnished studio in Marina Towers", "price": 65000, "usage_count": 12, "status": "active"},
    {"service_name": "2BR Family Suite", "description": "Spacious 2BR with sea view - Palm", "price": 145000, "usage_count": 8, "status": "active"},
    {"service_name": "Retail Space - Ground", "description": "Prime retail location in Business Bay", "price": 280000, "usage_count": 3, "status": "active"},
    {"service_name": "Short-term Stay (Daily)", "description": "Luxury serviced apartment stays", "price": 850, "usage_count": 112, "status": "active"},
    {"service_name": "Maintenance Package", "description": "Annual home maintenance and repair", "price": 3500, "usage_count": 45, "status": "active"},
    {"service_name": "Parking Slot - VIP", "description": "Dedicated underground parking spot", "price": 5000, "usage_count": 20, "status": "active"},
    {"service_name": "Penthouse - Executive", "description": "Exclusive 4BR penthouse with private pool", "price": 450000, "usage_count": 1, "status": "inactive"},
]

BANK_ACCOUNTS = [
    {"account_name": "Escrow Rental Account", "bank_name": "Emirates NBD", "account_number": "XXXX-9988", "balance": 4250000, "account_type": "current"},
    {"account_name": "Property Mgmt Fund", "bank_name": "ADCB", "account_number": "XXXX-7766", "balance": 850000, "account_type": "savings"},
    {"account_name": "Maintenance Ops", "bank_name": "Dubai Islamic Bank", "account_number": "XXXX-4433", "balance": 120000, "account_type": "current"},
]

SERVICE_NAMES = [s["service_name"] for s in SERVICES]
CLIENT_NAMES = [c["client_name"] for c in CLIENTS]



def _generate_invoices(count: int = 50):
    """Generate realistic invoice records."""
    statuses = ["paid", "unpaid", "overdue", "partial"]
    invoices = []
    for i in range(1, count + 1):
        issue_date = datetime.now() - timedelta(days=random.randint(1, 120))
        due_date   = issue_date + timedelta(days=30)
        status     = random.choice(statuses)
        total      = random.randint(10000, 150000)

        invoices.append({
            "invoice_number": f"INV-{1000 + i}",
            "client_name":    random.choice(CLIENT_NAMES),
            "total":          total,
            "status":         status,
            "issue_date":     issue_date,
            "due_date":       due_date,
            "services":       random.sample(SERVICE_NAMES, k=random.randint(1, 3)),
        })
    return invoices


def _generate_transactions(count: int = 80):
    """Generate realistic banking transactions."""
    account_names = [a["account_name"] for a in BANK_ACCOUNTS]
    descriptions  = [
        "Monthly rent received", "Maintenance service payout",
        "Utility bill payment (DEWA)", "Lease renewal fee",
        "Security deposit received", "Property management fee",
        "A/C Repair payment", "Escrow transfer",
    ]
    transactions = []
    for i in range(1, count + 1):
        txn_type = random.choice(["credit", "debit"])
        transactions.append({
            "transaction_id": f"TXN-{5000 + i}",
            "account_name":   random.choice(account_names),
            "type":           txn_type,
            "amount":         random.randint(1000, 80000),
            "date":           datetime.now() - timedelta(days=random.randint(1, 90)),
            "description":    random.choice(descriptions),
        })
    return transactions


# ── Main Seed Function ─────────────────────────────────────────────

def seed_database():
    """Drop and re‑seed all collections with mock data."""

    # Clear existing data
    for col in [invoice_collection, client_collection, vendor_collection,
                service_collection, banking_collection, transaction_collection]:
        col.delete_many({})

    # Insert data
    client_collection.insert_many([{**c, "created_at": datetime.now()} for c in CLIENTS])
    vendor_collection.insert_many([{**v, "created_at": datetime.now()} for v in VENDORS])
    service_collection.insert_many(SERVICES)
    banking_collection.insert_many(BANK_ACCOUNTS)

    invoices = _generate_invoices(50)
    invoice_collection.insert_many(invoices)

    transactions = _generate_transactions(80)
    transaction_collection.insert_many(transactions)

    print("--- Database seeded ---")
    print(f"   * {len(CLIENTS)} clients")
    print(f"   * {len(VENDORS)} vendors")
    print(f"   * {len(SERVICES)} services")
    print(f"   * {len(BANK_ACCOUNTS)} bank accounts")
    print(f"   * {len(invoices)} invoices")
    print(f"   * {len(transactions)} transactions")

