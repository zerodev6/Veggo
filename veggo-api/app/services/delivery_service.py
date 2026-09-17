import math
from typing import Any, Dict, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings

# Store default origin (e.g. Central Warehouse / Hub in Nuwara Eliya / Kandy, Sri Lanka)
STORE_LATITUDE = 6.9497
STORE_LONGITUDE = 80.7891


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points on Earth in kilometers."""
    R = 6371.0  # Earth's radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


class DeliveryService:
    @staticmethod
    async def estimate_delivery_fee(
        db: AsyncIOMotorDatabase,
        subtotal: float,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        district: Optional[str] = None,
        city: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculates delivery fee based on:
        - Free delivery threshold
        - Configured service areas
        - Coordinate distance (km) or base fee
        """
        # 1. Check free delivery threshold
        if subtotal >= settings.FREE_DELIVERY_THRESHOLD:
            return {
                "distance_km": 0.0,
                "delivery_fee": 0.0,
                "is_serviceable": True,
                "reason": f"Free delivery on orders above Rs. {settings.FREE_DELIVERY_THRESHOLD:.2f}"
            }

        # 2. Check if a district/city specific service area rule exists
        if district:
            service_area = await db.service_areas.find_one({
                "$or": [
                    {"name": {"$regex": f"^{district}$", "$options": "i"}},
                    {"district": {"$regex": f"^{district}$", "$options": "i"}},
                    {"city": {"$regex": f"^{city}$", "$options": "i"}} if city else {}
                ],
                "is_active": True
            })
            if service_area:
                custom_fee = service_area.get("delivery_fee")
                if custom_fee is not None:
                    return {
                        "distance_km": 0.0,
                        "delivery_fee": float(custom_fee),
                        "is_serviceable": True,
                        "reason": f"Standard flat rate for {service_area.get('name')}"
                    }

        # 3. Distance based estimation if coordinates provided
        if latitude is not None and longitude is not None:
            distance_km = calculate_haversine_distance(
                STORE_LATITUDE, STORE_LONGITUDE,
                latitude, longitude
            )
            
            if distance_km > settings.MAX_DELIVERY_DISTANCE_KM:
                return {
                    "distance_km": distance_km,
                    "delivery_fee": 0.0,
                    "is_serviceable": False,
                    "reason": f"Location ({distance_km} km) exceeds maximum delivery radius of {settings.MAX_DELIVERY_DISTANCE_KM} km."
                }
                
            fee = settings.BASE_DELIVERY_FEE + (distance_km * settings.PER_KM_DELIVERY_FEE)
            return {
                "distance_km": distance_km,
                "delivery_fee": round(fee, 2),
                "is_serviceable": True,
                "reason": f"Distance-based delivery rate for {distance_km} km"
            }

        # 4. Fallback to base delivery fee
        return {
            "distance_km": 0.0,
            "delivery_fee": float(settings.BASE_DELIVERY_FEE),
            "is_serviceable": True,
            "reason": "Standard base delivery fee"
        }


delivery_service = DeliveryService()
