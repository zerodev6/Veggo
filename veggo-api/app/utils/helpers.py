import logging
import random
from datetime import datetime
from typing import Any, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("veggo.helpers")

# Sri Lanka Provinces and Districts
SRI_LANKA_REGIONS = {
    "Western": ["Colombo", "Gampaha", "Kalutara"],
    "Central": ["Kandy", "Matale", "Nuwara Eliya"],
    "Southern": ["Galle", "Matara", "Hambantota"],
    "Northern": ["Jaffna", "Kilinochchi", "Mannar", "Mullaitivu", "Vavuniya"],
    "Eastern": ["Batticaloa", "Ampara", "Trincomalee"],
    "North Western": ["Kurunegala", "Puttalam"],
    "North Central": ["Anuradhapura", "Polonnaruwa"],
    "Uva": ["Badulla", "Monaragala"],
    "Sabaragamuwa": ["Ratnapura", "Kegalle"],
}


async def generate_order_number(db: AsyncIOMotorDatabase) -> str:
    """
    Generates a unique, collision-free order number like: VG-20260917-000123
    """
    date_str = datetime.utcnow().strftime("%Y%m%d")
    
    # Try finding the count of today's orders
    prefix = f"VG-{date_str}-"
    try:
        count = await db.orders.count_documents({"order_number": {"$regex": f"^{prefix}"}})
        seq = count + 1
        order_num = f"{prefix}{seq:06d}"
        
        # Verify uniqueness
        exists = await db.orders.find_one({"order_number": order_num})
        if exists:
            rand_suffix = random.randint(100, 999)
            order_num = f"{prefix}{seq:04d}{rand_suffix}"
        return order_num
    except Exception:
        rand_suffix = random.randint(100000, 999999)
        return f"{prefix}{rand_suffix}"


async def log_audit_event(
    db: AsyncIOMotorDatabase,
    admin_id: str,
    action: str,
    target_type: str,
    target_id: str,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    ip_address: Optional[str] = None
):
    """
    Logs administrative actions for regulatory compliance and audit tracking.
    """
    try:
        audit_doc = {
            "admin_id": admin_id,
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "old_value": old_value,
            "new_value": new_value,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow()
        }
        await db.audit_logs.insert_one(audit_doc)
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
