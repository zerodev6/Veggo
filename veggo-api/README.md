# VEGGO 🇱🇰 — Online Vegetable & Grocery Ordering Platform API

Production-ready backend API built for **VEGGO**, Sri Lanka's premier online fresh vegetable and grocery ordering platform. Designed for seamless native Android customer applications, real-time delivery rider dispatch, and centralized web admin portals.

---

## 1. Project Overview

VEGGO connects Sri Lankan households directly with farm-fresh produce from Nuwara Eliya, Dambulla, and local growers.

Key capabilities:
- **Sri Lanka Weight Ordering**: Order exact gram quantities (100g, 250g, 500g, 750g, 1kg, 2kg, or custom grams).
- **Automated Pricing**: Server-enforced pricing (e.g., Nuwara Eliya Carrots @ Rs. 450/kg; 750g calculated automatically as `(450 / 1000) * 750 = Rs. 337.50`). Never trusts client totals.
- **Atomic Stock Reservation**: Prevents overselling using atomic MongoDB operations (`$inc` condition checks).
- **Google Sign-In with ID Token Verification**: Validates Android Google tokens via Google's OAuth2 cryptographic libraries and manages identity linking.
- **Sri Lankan Deliveries**: Distinguishes provinces, districts, cities, and distance-based fees with a configurable free delivery threshold (default Rs. 5,000).
- **Order Lifecycle & Tracking**: Real-time state machine (`PLACED` → `CONFIRMED` → `PREPARING` → `READY_FOR_PICKUP` → `OUT_FOR_DELIVERY` → `DELIVERED`).
- **Delivery Agent Portal**: Live rider dispatch, GPS location broadcasting, and one-tap delivery completion.
- **Admin Dashboard**: Revenue reports, stock alerts, price history audit trails, coupon management, and store hour toggles.

---

## 2. Technology Stack

- **Runtime**: Python 3.11+
- **Framework**: FastAPI (High-performance Async ASGI)
- **Server**: Uvicorn
- **Database**: MongoDB via Motor (Async PyMongo driver)
- **Validation**: Pydantic v2
- **Auth**: PyJWT (HMAC-SHA256) + Passlib (Bcrypt) + Google Auth
- **Deployment**: Koyeb (Port 8000), Render, Railway, Docker

---

## 3. Environment Variables

Create `.env` inside `veggo-api/`:

```env
# MongoDB
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=veggo

# Security & JWT
JWT_SECRET=super_secret_jwt_key_sri_lanka_2026
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Google Authentication
GOOGLE_WEB_CLIENT_ID=your-google-web-client-id.apps.googleusercontent.com
GOOGLE_ANDROID_CLIENT_ID=your-google-android-client-id.apps.googleusercontent.com

# Server & Network
ALLOWED_ORIGINS=*
PORT=8000
HOST=0.0.0.0

# Store Configuration (Sri Lanka)
STORE_NAME=Veggo
CURRENCY=LKR
STORE_PHONE=+94771234567
STORE_EMAIL=support@veggo.lk
STORE_ADDRESS=No. 45, Nuwara Eliya Road, Kandy, Sri Lanka

# Delivery Parameters
BASE_DELIVERY_FEE=150
FREE_DELIVERY_THRESHOLD=5000
PER_KM_DELIVERY_FEE=50
MAX_DELIVERY_DISTANCE_KM=25
```

---

## 4. Local Installation & Running

### Step 1: Clone and setup virtual environment
```bash
cd veggo-api
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Seed the Database
Populate categories, sample vegetables, default users, coupons, and service areas:
```bash
python seed.py
```

Default credentials created by `seed.py`:
- **Admin**: `admin@veggo.lk` / `Admin@123456`
- **Delivery Agent**: `agent@veggo.lk` / `Agent@123456`
- **Customer**: `customer@veggo.lk` / `Customer@123`

### Step 3: Start the API
```bash
# Run locally on port 8000
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger documentation will be accessible at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health: `http://localhost:8000/health`

---

## 5. Deployment on Koyeb (Port 8000)

Veggo is pre-configured with `koyeb.yaml`, `Dockerfile`, and `Procfile` ready for 1-click Koyeb hosting on **Port 8000**.

### Method A: Deploy via Koyeb CLI
```bash
koyeb app init veggo-api --docker Dockerfile --port 8000:http --route /:8000 --env PORT=8000 --env MONGO_URI="<YOUR_MONGO_URI>"
```

### Method B: Deploy via Koyeb Web Console (GitHub repo)
1. In Koyeb Console, click **Create Service** → **GitHub**.
2. Select repository and set **Root Directory** to `veggo-api` (or root).
3. Set **Port** to `8000`.
4. Add Environment Variables:
   - `MONGO_URI`: Your MongoDB Atlas connection string
   - `JWT_SECRET`: Random 64-character secret
   - `PORT`: `8000`
5. Click **Deploy**. Koyeb will run health check at `/health` and start the service.

---

## 6. Docker Deployment

### Build the Image:
```bash
docker build -t veggo-api .
```

### Run Container on Port 8000:
```bash
docker run -d -p 8000:8000 \
  -e PORT=8000 \
  -e MONGO_URI="mongodb://host.docker.internal:27017" \
  -e JWT_SECRET="your-jwt-secret" \
  --name veggo-backend veggo-api
```

---

## 7. Android Application Integration Guide

### 1. Base URL
Point Retrofit or Ktor HTTP client to your deployed Koyeb endpoint:
```kotlin
const val BASE_URL = "https://your-app.koyeb.app/"
```

### 2. Authentication
Send `Authorization: Bearer <TOKEN>` header for all authenticated endpoints.

### 3. Adding Custom Grams to Cart
Send quantity as exact grams with unit `"g"`:
```json
POST /api/cart/items
{
  "product_id": "66e921b7...",
  "quantity": 750,
  "unit": "g"
}
```

The server calculates the price automatically and returns updated cart totals in LKR.

### 4. Checkout
```json
POST /api/orders/checkout
{
  "address_id": "66e922c1...",
  "payment_method": "COD",
  "coupon_code": "VEGGO100",
  "delivery_note": "Please leave at gate"
}
```

---

## 8. Automated Tests

Run the test suite with pytest:
```bash
pytest
```
Tests verify:
- Sri Lankan phone validation (`07XXXXXXXX`)
- Password hashing & JWT generation
- Weight calculation math (750g @ 450/kg = 337.50)
- Cart recalculation
- Order status transition guardrails
- Delivery Haversine distance calculations

---

## 9. License

Proprietary © 2026 VEGGO Sri Lanka. All Rights Reserved.
