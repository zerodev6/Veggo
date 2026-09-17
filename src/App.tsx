import React, { useState } from "react";
import {
  Server,
  Terminal,
  ShieldCheck,
  CheckCircle2,
  Copy,
  ExternalLink,
  Layers,
  Cpu,
  Smartphone,
  Tag,
  Truck,
  Database,
  ArrowRight,
  Code2,
  Sparkles,
  RefreshCw,
  Scale
} from "lucide-react";

export default function App() {
  const [activeTab, setActiveTab] = useState<"koyeb" | "explorer" | "android" | "credentials">("koyeb");
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // Weight calculator test state
  const [testWeightGrams, setTestWeightGrams] = useState<number>(750);
  const [testPricePerKg, setTestPricePerKg] = useState<number>(450);

  // Delivery distance test state
  const [testDistanceKm, setTestDistanceKm] = useState<number>(8.5);
  const [testSubtotal, setTestSubtotal] = useState<number>(2400);

  // Coupon simulator state
  const [testCoupon, setTestCoupon] = useState<string>("FRESH20");

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(id);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const calculatedWeightPrice = ((testPricePerKg / 1000) * testWeightGrams).toFixed(2);
  const calculatedDeliveryFee = testSubtotal >= 5000 ? 0 : 150 + Math.max(0, testDistanceKm - 5) * 50;

  return (
    <div className="min-h-screen bg-stone-950 text-stone-100 font-sans antialiased selection:bg-emerald-500 selection:text-black">
      {/* Top Banner */}
      <header className="border-b border-stone-800 bg-stone-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-950/50">
              <span className="text-xl">🥬</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-stone-50 tracking-tight">VEGGO Sri Lanka</span>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Backend API v1.0.0
                </span>
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  Port 8000
                </span>
              </div>
              <p className="text-xs text-stone-400 hidden sm:block">
                Production-ready Vegetable & Grocery Ordering Platform Engine
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="#koyeb-guide"
              onClick={() => setActiveTab("koyeb")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-stone-950 text-sm font-semibold transition shadow-md shadow-emerald-500/10"
            >
              <Server className="w-4 h-4" />
              <span>Deploy on Koyeb</span>
            </a>
          </div>
        </div>
      </header>

      {/* Hero Header */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-4">
        <div className="p-6 sm:p-8 rounded-2xl bg-gradient-to-br from-stone-900 via-stone-900 to-emerald-950/40 border border-stone-800 relative overflow-hidden">
          <div className="max-w-3xl relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Configured for Koyeb Deployment on Port 8000</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight leading-snug">
              VEGGO Grocery Platform Backend
            </h1>
            <p className="mt-2 text-sm sm:text-base text-stone-300 leading-relaxed">
              Complete backend architecture featuring Sri Lankan custom gram pricing (e.g. 750g carrots),
              atomic MongoDB stock reservation, Google Sign-In with ID token verification, multi-tier delivery distance estimation, and native Android support.
            </p>

            <div className="mt-5 flex flex-wrap gap-4 text-xs text-stone-400">
              <div className="flex items-center gap-1.5 bg-stone-950/60 px-3 py-1.5 rounded-lg border border-stone-800">
                <Cpu className="w-4 h-4 text-emerald-400" />
                <span>FastAPI + Async Motor (MongoDB)</span>
              </div>
              <div className="flex items-center gap-1.5 bg-stone-950/60 px-3 py-1.5 rounded-lg border border-stone-800">
                <ShieldCheck className="w-4 h-4 text-blue-400" />
                <span>JWT + Google Auth + RBAC</span>
              </div>
              <div className="flex items-center gap-1.5 bg-stone-950/60 px-3 py-1.5 rounded-lg border border-stone-800">
                <Truck className="w-4 h-4 text-amber-400" />
                <span>Sri Lanka Delivery Engine</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
        <div className="flex border-b border-stone-800 gap-2 sm:gap-4 overflow-x-auto">
          <button
            id="tab-koyeb"
            onClick={() => setActiveTab("koyeb")}
            className={`pb-3 px-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition whitespace-nowrap ${
              activeTab === "koyeb"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-stone-400 hover:text-stone-200"
            }`}
          >
            <Server className="w-4 h-4" />
            <span>Koyeb Deployment (Port 8000)</span>
          </button>

          <button
            id="tab-explorer"
            onClick={() => setActiveTab("explorer")}
            className={`pb-3 px-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition whitespace-nowrap ${
              activeTab === "explorer"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-stone-400 hover:text-stone-200"
            }`}
          >
            <Scale className="w-4 h-4" />
            <span>Weight & Engine Simulator</span>
          </button>

          <button
            id="tab-android"
            onClick={() => setActiveTab("android")}
            className={`pb-3 px-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition whitespace-nowrap ${
              activeTab === "android"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-stone-400 hover:text-stone-200"
            }`}
          >
            <Smartphone className="w-4 h-4" />
            <span>Android Integration</span>
          </button>

          <button
            id="tab-credentials"
            onClick={() => setActiveTab("credentials")}
            className={`pb-3 px-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition whitespace-nowrap ${
              activeTab === "credentials"
                ? "border-emerald-500 text-emerald-400"
                : "border-transparent text-stone-400 hover:text-stone-200"
            }`}
          >
            <Database className="w-4 h-4" />
            <span>Seed Data & Access Keys</span>
          </button>
        </div>
      </div>

      {/* Tab Contents */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "koyeb" && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-5 rounded-xl bg-stone-900 border border-stone-800">
                <div className="text-xs uppercase tracking-wider text-stone-500 font-semibold mb-1">Target Host</div>
                <div className="text-lg font-bold text-white flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  Koyeb Cloud
                </div>
                <p className="text-xs text-stone-400 mt-2">Serverless container platform with native health checking.</p>
              </div>

              <div className="p-5 rounded-xl bg-stone-900 border border-stone-800">
                <div className="text-xs uppercase tracking-wider text-stone-500 font-semibold mb-1">Configured Port</div>
                <div className="text-lg font-bold text-emerald-400 flex items-center gap-2">
                  <span>8000 / TCP</span>
                </div>
                <p className="text-xs text-stone-400 mt-2">Set in Dockerfile, Procfile, and koyeb.yaml routing.</p>
              </div>

              <div className="p-5 rounded-xl bg-stone-900 border border-stone-800">
                <div className="text-xs uppercase tracking-wider text-stone-500 font-semibold mb-1">Health Check</div>
                <div className="text-lg font-bold text-blue-400 flex items-center gap-2">
                  <span>GET /health</span>
                </div>
                <p className="text-xs text-stone-400 mt-2">Returns API & MongoDB connectivity status.</p>
              </div>
            </div>

            {/* Koyeb CLI & Docker Instructions */}
            <div className="p-6 rounded-xl bg-stone-900 border border-stone-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-emerald-400" />
                  Koyeb CLI 1-Command Deployment
                </h3>
                <button
                  id="copy-koyeb-cmd"
                  onClick={() =>
                    copyToClipboard(
                      "koyeb app init veggo-api --docker Dockerfile --port 8000:http --route /:8000 --env PORT=8000 --env MONGO_URI=\"mongodb+srv://...\"",
                      "koyeb-cmd"
                    )
                  }
                  className="text-xs flex items-center gap-1 text-stone-400 hover:text-white px-2 py-1 rounded bg-stone-800"
                >
                  {copiedText === "koyeb-cmd" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedText === "koyeb-cmd" ? "Copied!" : "Copy"}</span>
                </button>
              </div>
              <pre className="p-3.5 rounded-lg bg-stone-950 font-mono text-xs text-emerald-300 overflow-x-auto border border-stone-800">
{`koyeb app init veggo-api \\
  --docker Dockerfile \\
  --port 8000:http \\
  --route /:8000 \\
  --env PORT=8000 \\
  --env MONGO_URI="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority" \\
  --env JWT_SECRET="your-super-secret-key-32-chars-long"`}
              </pre>
            </div>

            {/* koyeb.yaml configuration preview */}
            <div className="p-6 rounded-xl bg-stone-900 border border-stone-800 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-emerald-400" />
                  Generated koyeb.yaml (Port 8000)
                </h3>
                <button
                  id="copy-koyeb-yaml"
                  onClick={() =>
                    copyToClipboard(
`name: veggo-api
services:
  - name: api
    type: web
    dockerfile: Dockerfile
    ports:
      - port: 8000
        protocol: http
    routes:
      - path: /
        port: 8000
    health_checks:
      - http:
          path: /health
          port: 8000
        interval: 30
    env:
      - key: PORT
        value: "8000"`,
                      "koyeb-yaml"
                    )
                  }
                  className="text-xs flex items-center gap-1 text-stone-400 hover:text-white px-2 py-1 rounded bg-stone-800"
                >
                  {copiedText === "koyeb-yaml" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedText === "koyeb-yaml" ? "Copied!" : "Copy"}</span>
                </button>
              </div>
              <pre className="p-3.5 rounded-lg bg-stone-950 font-mono text-xs text-stone-300 overflow-x-auto border border-stone-800">
{`name: veggo-api
services:
  - name: api
    type: web
    dockerfile: Dockerfile
    ports:
      - port: 8000
        protocol: http
    routes:
      - path: /
        port: 8000
    health_checks:
      - http:
          path: /health
          port: 8000
        interval: 30
    env:
      - key: PORT
        value: "8000"
      - key: STORE_NAME
        value: "Veggo"
      - key: CURRENCY
        value: "LKR"`}
              </pre>
            </div>
          </div>
        )}

        {activeTab === "explorer" && (
          <div className="space-y-6">
            {/* Sri Lanka Gram Weight Calculator */}
            <div className="p-6 rounded-xl bg-stone-900 border border-stone-800 space-y-4">
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Custom Weight Engine (Server Formula Verification)</h3>
              </div>
              <p className="text-xs text-stone-400">
                Tests the exact Python pricing service method: <code className="text-emerald-300">line_price = round((price_per_kg / 1000.0) * quantity_in_grams, 2)</code>.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-stone-400 mb-1">Product Price Per 1kg (LKR)</label>
                  <input
                    id="input-price-per-kg"
                    type="number"
                    value={testPricePerKg}
                    onChange={(e) => setTestPricePerKg(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-stone-950 border border-stone-800 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                  <span className="text-[11px] text-stone-500">e.g. Nuwara Eliya Carrots: Rs. 450</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-stone-400 mb-1">Ordered Weight (Grams)</label>
                  <div className="flex gap-2">
                    <input
                      id="input-grams"
                      type="number"
                      value={testWeightGrams}
                      onChange={(e) => setTestWeightGrams(Number(e.target.value))}
                      className="w-full px-3 py-2 bg-stone-950 border border-stone-800 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div className="flex gap-1.5 mt-1.5">
                    {[100, 250, 500, 750, 1000].map((g) => (
                      <button
                        key={g}
                        onClick={() => setTestWeightGrams(g)}
                        className="px-2 py-0.5 text-[11px] bg-stone-800 hover:bg-stone-700 text-stone-300 rounded"
                      >
                        {g}g
                      </button>
                    ))}
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/30 flex flex-col justify-between">
                  <div className="text-xs text-emerald-400 font-semibold">Calculated Server Price</div>
                  <div className="text-2xl font-extrabold text-white">
                    Rs. {calculatedWeightPrice}
                    <span className="text-xs font-normal text-stone-400 ml-1">LKR</span>
                  </div>
                  <div className="text-[11px] text-stone-400">
                    Formula: ({testPricePerKg} / 1000) × {testWeightGrams}g
                  </div>
                </div>
              </div>
            </div>

            {/* Sri Lanka Delivery & Haversine Simulator */}
            <div className="p-6 rounded-xl bg-stone-900 border border-stone-800 space-y-4">
              <div className="flex items-center gap-2">
                <Truck className="w-5 h-5 text-amber-400" />
                <h3 className="text-base font-bold text-white">Sri Lanka Delivery Fee & Threshold Estimator</h3>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-stone-400 mb-1">Cart Subtotal (LKR)</label>
                  <input
                    id="input-subtotal"
                    type="number"
                    value={testSubtotal}
                    onChange={(e) => setTestSubtotal(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-stone-950 border border-stone-800 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                  <span className="text-[11px] text-stone-500">Free delivery threshold is Rs. 5,000</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-stone-400 mb-1">Delivery Distance (KM)</label>
                  <input
                    id="input-distance"
                    type="number"
                    step="0.5"
                    value={testDistanceKm}
                    onChange={(e) => setTestDistanceKm(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-stone-950 border border-stone-800 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500"
                  />
                  <span className="text-[11px] text-stone-500">First 5km = Rs. 150 base; +Rs. 50/km after</span>
                </div>

                <div className="p-4 rounded-lg bg-amber-950/20 border border-amber-500/30 flex flex-col justify-between">
                  <div className="text-xs text-amber-400 font-semibold">Delivery Fee</div>
                  <div className="text-2xl font-extrabold text-white">
                    {testSubtotal >= 5000 ? (
                      <span className="text-emerald-400">FREE</span>
                    ) : (
                      `Rs. ${calculatedDeliveryFee.toFixed(2)}`
                    )}
                  </div>
                  <div className="text-[11px] text-stone-400">
                    {testSubtotal >= 5000 ? "Eligible for free delivery" : "Standard Sri Lankan tiered fee"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "android" && (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-stone-900 border border-stone-800 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Smartphone className="w-4 h-4 text-emerald-400" />
                    Android Retrofit Interface (Kotlin)
                  </h3>
                  <p className="text-xs text-stone-400 mt-1">Ready to copy directly into your Android Studio project.</p>
                </div>
                <button
                  id="copy-android-kotlin"
                  onClick={() =>
                    copyToClipboard(
`package lk.veggo.network

import retrofit2.http.*

interface VeggoApiService {
    @GET("api/products")
    suspend fun getProducts(
        @Query("category_id") categoryId: String? = null,
        @Query("page") page: Int = 1
    ): ApiResponse<PaginatedResponse<ProductDto>>

    @POST("api/cart/items")
    suspend fun addToCart(
        @Header("Authorization") token: String,
        @Body request: AddToCartRequest
    ): ApiResponse<CartResponse>

    @POST("api/orders/checkout")
    suspend fun checkout(
        @Header("Authorization") token: String,
        @Body request: CheckoutRequest
    ): ApiResponse<OrderResponse>
}

data class AddToCartRequest(
    val product_id: String,
    val quantity: Double, // 750 for grams
    val unit: String      // "g", "kg", "piece", "pack"
)`,
                      "android-code"
                    )
                  }
                  className="text-xs flex items-center gap-1 text-stone-400 hover:text-white px-2.5 py-1.5 rounded bg-stone-800"
                >
                  {copiedText === "android-code" ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedText === "android-code" ? "Copied!" : "Copy Kotlin"}</span>
                </button>
              </div>

              <pre className="p-4 rounded-lg bg-stone-950 font-mono text-xs text-stone-300 overflow-x-auto border border-stone-800 leading-relaxed">
{`package lk.veggo.network

import retrofit2.http.*

interface VeggoApiService {
    @GET("api/products")
    suspend fun getProducts(
        @Query("category_id") categoryId: String? = null,
        @Query("page") page: Int = 1
    ): ApiResponse<PaginatedResponse<ProductDto>>

    @POST("api/cart/items")
    suspend fun addToCart(
        @Header("Authorization") token: String,
        @Body request: AddToCartRequest
    ): ApiResponse<CartResponse>

    @POST("api/orders/checkout")
    suspend fun checkout(
        @Header("Authorization") token: String,
        @Body request: CheckoutRequest
    ): ApiResponse<OrderResponse>
}

data class AddToCartRequest(
    val product_id: String,
    val quantity: Double, // 750 for 750g
    val unit: String      // "g" or "kg"
)`}
              </pre>
            </div>
          </div>
        )}

        {activeTab === "credentials" && (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-stone-900 border border-stone-800 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                Pre-seeded Roles & Credentials
              </h3>
              <p className="text-xs text-stone-400">
                These test accounts are automatically created when you run <code className="text-emerald-300">python seed.py</code>:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div className="p-4 rounded-lg bg-stone-950 border border-stone-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-emerald-400">Administrator</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">ADMIN</span>
                  </div>
                  <div className="text-xs text-stone-300 font-mono">admin@veggo.lk</div>
                  <div className="text-xs text-stone-400 font-mono">Password: Admin@123456</div>
                  <div className="text-[11px] text-stone-500">Access to dashboard, product management, and orders.</div>
                </div>

                <div className="p-4 rounded-lg bg-stone-950 border border-stone-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-blue-400">Delivery Rider</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">DELIVERY_AGENT</span>
                  </div>
                  <div className="text-xs text-stone-300 font-mono">agent@veggo.lk</div>
                  <div className="text-xs text-stone-400 font-mono">Password: Agent@123456</div>
                  <div className="text-[11px] text-stone-500">Rider order acceptance and GPS broadcast.</div>
                </div>

                <div className="p-4 rounded-lg bg-stone-950 border border-stone-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-amber-400">Customer</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">USER</span>
                  </div>
                  <div className="text-xs text-stone-300 font-mono">customer@veggo.lk</div>
                  <div className="text-xs text-stone-400 font-mono">Password: Customer@123</div>
                  <div className="text-[11px] text-stone-500">Can add items, checkout with COD or Bank Transfer.</div>
                </div>
              </div>
            </div>

            <div className="p-6 rounded-xl bg-stone-900 border border-stone-800 space-y-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Tag className="w-4 h-4 text-emerald-400" />
                Pre-seeded Promotional Coupons
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3 rounded-lg bg-stone-950 border border-stone-800 flex items-center justify-between">
                  <div>
                    <div className="font-mono text-sm font-bold text-emerald-400">VEGGO100</div>
                    <div className="text-xs text-stone-400">Flat Rs. 100 off on orders over Rs. 1,000</div>
                  </div>
                  <button
                    onClick={() => copyToClipboard("VEGGO100", "c-100")}
                    className="text-xs px-2.5 py-1 bg-stone-800 text-stone-300 rounded hover:bg-stone-700"
                  >
                    {copiedText === "c-100" ? "Copied" : "Copy"}
                  </button>
                </div>

                <div className="p-3 rounded-lg bg-stone-950 border border-stone-800 flex items-center justify-between">
                  <div>
                    <div className="font-mono text-sm font-bold text-emerald-400">FRESH20</div>
                    <div className="text-xs text-stone-400">20% off up to Rs. 600 on orders over Rs. 2,000</div>
                  </div>
                  <button
                    onClick={() => copyToClipboard("FRESH20", "c-20")}
                    className="text-xs px-2.5 py-1 bg-stone-800 text-stone-300 rounded hover:bg-stone-700"
                  >
                    {copiedText === "c-20" ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-stone-800 mt-12 py-6 text-center text-xs text-stone-500">
        VEGGO Sri Lanka Grocery API Engine & Developer Portal • Configured for Koyeb Port 8000
      </footer>
    </div>
  );
}
