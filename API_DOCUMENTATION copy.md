# Perfume Price Tracker — REST API Documentation

**Project:** Web Application Development / HW4  
**Base URL:** `http://localhost:5051`  
**Request body format:** `Content-Type: application/json` for POST and PUT  
**Backend:** Flask + psycopg2  
**Database:** PostgreSQL (`postgres_sabog_table`, `retailers`, `price_offers`)

This document describes **19 distinct method/path endpoints**. Example IDs and responses are illustrative; the actual database assigns IDs dynamically. Prices are manually recorded until a future price-fetching feature is integrated.

## 1. Data model and relationships

### 1.1 Perfume (`postgres_sabog_table`)

| Field | Database type | Required on POST / PUT | Rule |
|---|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | No | Generated |
| `brand` | `VARCHAR(100)` | Yes | Non-empty string |
| `name` | `VARCHAR(150)` | Yes | Non-empty string |
| `concentration` | `VARCHAR(30)` | No | String or null |
| `volume_ml` | `INTEGER` | No | Positive integer or null |
| `remaining_ml` | `INTEGER` | No | Non-negative integer; only if `owned`; requires `volume_ml` and cannot exceed it |
| `top_notes` | `TEXT` | No | String or null |
| `heart_notes` | `TEXT` | No | String or null |
| `base_notes` | `TEXT` | No | String or null |
| `fragrance_family` | `VARCHAR(100)` | No | String or null |
| `status` | `VARCHAR(20)` | Yes | `owned`, `wishlist`, or `want_to_test` |

### 1.2 Retailer (`retailers`)

| Field | Database type | Required on POST / PUT | Rule |
|---|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | No | Generated |
| `name` | `VARCHAR(150) UNIQUE NOT NULL` | Yes | Non-empty string; trimmed; length ≤ 150 |
| `website_url` | `TEXT NOT NULL` | Yes | `http://` or `https://` URL with a hostname |
| `created_at` | `TIMESTAMPTZ` | No | Generated on insert |

### 1.3 PriceOffer (`price_offers`)

| Field | Database type | Required on POST / PUT | Rule |
|---|---|---|---|
| `id` | `SERIAL PRIMARY KEY` | No | Generated |
| `perfume_id` | `INTEGER NOT NULL`, FK | Yes | Positive integer referring to existing perfume |
| `retailer_id` | `INTEGER NOT NULL`, FK | Yes | Positive integer referring to existing retailer |
| `volume_ml` | `INTEGER NOT NULL` | Yes | Positive integer; the offered bottle size |
| `price_kzt` | `NUMERIC(12,2) NOT NULL` | Yes | Positive monetary value with max 2 decimal places |
| `product_url` | `TEXT NOT NULL` | Yes | `http://` or `https://` URL with hostname |
| `is_available` | `BOOLEAN NOT NULL` | No | Defaults to `true` |
| `checked_at` | `TIMESTAMPTZ NOT NULL` | No | Insert timestamp, refreshed on PUT |

**Foreign keys:** `price_offers.perfume_id → postgres_sabog_table.id` (`ON DELETE CASCADE`); `price_offers.retailer_id → retailers.id` (`ON DELETE RESTRICT`). There is a unique constraint on `(perfume_id, retailer_id, volume_ml)`.

**Important semantics:** `checked_at` currently records the time an offer was entered or updated. It does not mean the retailer's live price was independently verified at that time. The `is_available` flag is provided by the API caller.

## 2. Response conventions

| Code | Meaning | Example situation |
|---|---|---|
| `200` | OK | Successful GET, PUT, DELETE |
| `201` | Created | Successful POST |
| `400` | Bad Request | Invalid status, price, ID reference, input body |
| `404` | Not Found | ID does not exist; no matching available offers |
| `409` | Conflict | Duplicate name/offer; retailer referenced by offers |

Successful list requests return JSON arrays (`[]` when empty). Object requests return JSON objects. Most errors use `{"error":"..."}`. PostgreSQL `NUMERIC` values may be JSON strings (for example `"168000.00"`) to preserve decimal precision.

## 3. Health and perfumes — 6 endpoints

### 3.1 GET `/api/health`

Returns API status. **200**:

```json
{"project": "My Perfume Collection", "status": "ok"}
```

Health checks Flask responsiveness; they do not directly verify database connectivity.

### 3.2 GET `/api/perfumes`

Returns all perfumes ordered by ID. Optional query parameters:

| Query | Allowed values | Behavior |
|---|---|---|
| `status` | `owned`, `wishlist`, `want_to_test` | Filters by status |
| `low_stock` | `true`, `false` | `true` filters to `owned` perfumes below the threshold in `app.py`; `false` leaves this filter off |

```http
GET /api/perfumes
GET /api/perfumes?status=owned
GET /api/perfumes?status=owned&low_stock=true
```

**200:** JSON array of perfume objects. **400:** `{"error":"Invalid status"}` or `{"error":"low_stock must be true or false"}`.

**Threshold note:** The earlier public `app.py` implementation passes `30` to the low-stock SQL condition, although the older README stated 10. This documentation follows **30 ml** from that Python code; if your local `app.py` changed, its configured value is authoritative.

### 3.3 GET `/api/perfumes/<int:perfume_id>`

**200:** One perfume object. **404:**

```json
{"error":"Perfume not found"}
```

### 3.4 POST `/api/perfumes`

**Example request:**

```json
{
  "brand": "Test Brand",
  "name": "Temporary Demo Perfume",
  "concentration": "EDP",
  "volume_ml": 100,
  "remaining_ml": 95,
  "top_notes": "Bergamot",
  "heart_notes": "Rose",
  "base_notes": "Musk",
  "fragrance_family": "Floral",
  "status": "owned"
}
```

**201:** Created perfume object with generated `id`.

**400** examples:

```json
{"error":"JSON object required"}
```

```json
{"error":"brand is required"}
```

```json
{"error":"Invalid status"}
```

```json
{"error":"Only owned perfumes can have remaining_ml"}
```

`volume_ml` must be a positive integer when provided. `remaining_ml` must be non-negative and not exceed `volume_ml`. Optional note fields must be strings when non-null. Database length limits are enforced by PostgreSQL.

### 3.5 PUT `/api/perfumes/<int:perfume_id>`

Full update. Send `brand`, `name`, `status`, plus any optional values that should remain populated. **Omitted optional fields become null.**

```json
{
  "brand": "Test Brand",
  "name": "Temporary Demo Perfume Updated",
  "concentration": "EDP",
  "volume_ml": 100,
  "remaining_ml": 90,
  "status": "owned"
}
```

**200:** Updated object. **400:** Invalid data. **404:** `{"error":"Perfume not found"}`.

### 3.6 DELETE `/api/perfumes/<int:perfume_id>`

**200:**

```json
{"message":"Perfume deleted successfully","id":4}
```

**404:** Perfume not found. **Warning:** Deletes the perfume and, due to FK cascade, all associated price offers. Use temporary test records for demonstrations.

## 4. Retailers — 5 endpoints

### 4.1 GET `/api/retailers`

**200:** Array of retailer objects, ordered by `id`.

### 4.2 GET `/api/retailers/<int:retailer_id>`

**200:** Retailer object. **404:**

```json
{"error":"Retailer not found"}
```

### 4.3 POST `/api/retailers`

```json
{
  "name": "Example Perfume Shop",
  "website_url": "https://example.com"
}
```

**201:** Created retailer; `id` and `created_at` are assigned by database. **400:** `Retailer name is required`, `Website URL is required`, `Invalid website URL`, or `Retailer name is too long` (inside the `error` field). **409:**

```json
{"error":"Retailer with this name already exists"}
```

### 4.4 PUT `/api/retailers/<int:retailer_id>`

Requires both `name` and `website_url`:

```json
{
  "name": "Example Perfume Shop Updated",
  "website_url": "https://example.org"
}
```

**200:** Updated retailer. **400:** Validation error. **404:** Not found. **409:** Duplicate name.

### 4.5 DELETE `/api/retailers/<int:retailer_id>`

**200:**

```json
{"message":"Retailer deleted successfully","id":3}
```

**404:** Retailer not found. **409:**

```json
{"error":"Cannot delete retailer with existing price offers"}
```

The retailer remains present while `price_offers` rows refer to it (`ON DELETE RESTRICT`).

## 5. Price offers — 5 endpoints

### 5.1 GET `/api/price-offers`

**200:** Array of offers, ordered by `id`.

### 5.2 GET `/api/price-offers/<int:offer_id>`

**200:** Single offer. **404:**

```json
{"error":"Price offer not found"}
```

### 5.3 POST `/api/price-offers`

```json
{
  "perfume_id": 1,
  "retailer_id": 1,
  "volume_ml": 100,
  "price_kzt": 168000,
  "product_url": "https://goldapple.kz/82401500003-musc-ravageur",
  "is_available": true
}
```

**201:** Created price offer object, for example:

```json
{
  "id": 7,
  "perfume_id": 1,
  "retailer_id": 1,
  "volume_ml": 100,
  "price_kzt": "168000.00",
  "product_url": "https://goldapple.kz/82401500003-musc-ravageur",
  "is_available": true,
  "checked_at": "Thu, 12 Nov 2026 10:00:00 GMT"
}
```

Response timestamp format and actual IDs depend on Flask/PostgreSQL. **400:** Wrong types, nonpositive numbers, unsupported URL, or nonexistent foreign-key records. **409:** Another offer with the same perfume, retailer, and volume already exists.

Possible errors:

```json
{"error":"perfume_id must be a positive integer"}
```

```json
{"error":"Invalid price_kzt"}
```

```json
{"error":"Perfume or retailer does not exist"}
```

```json
{"error":"Price offer already exists for this perfume, retailer and volume"}
```

### 5.4 PUT `/api/price-offers/<int:offer_id>`

Full update; requires `perfume_id`, `retailer_id`, `volume_ml`, `price_kzt`, `product_url`. `is_available` defaults to `true` if omitted. Example:

```json
{
  "perfume_id": 1,
  "retailer_id": 1,
  "volume_ml": 100,
  "price_kzt": 170000,
  "product_url": "https://goldapple.kz/82401500003-musc-ravageur",
  "is_available": false
}
```

**200:** Updated offer with refreshed `checked_at`. **400:** Invalid data / FK. **404:** Offer not found. **409:** Unique constraint conflict.

### 5.5 DELETE `/api/price-offers/<int:offer_id>`

**200:**

```json
{"message":"Price offer deleted successfully","id":7}
```

**404:** Offer not found.

## 6. Relationship endpoints — 3 endpoints

### 6.1 GET `/api/perfumes/<int:perfume_id>/offers`

Returns **all** price offers for the specified perfume, with retailer information. Uses SQL `JOIN retailers` and sorts by volume, then price.

**200** response (example shortened):

```json
[
  {
    "id": 7,
    "perfume_id": 1,
    "retailer_id": 1,
    "retailer_name": "Golden Apple",
    "retailer_website": "https://goldapple.kz",
    "volume_ml": 100,
    "price_kzt": "168000.00",
    "product_url": "https://goldapple.kz/82401500003-musc-ravageur",
    "is_available": true,
    "checked_at": "Thu, 12 Nov 2026 10:00:00 GMT"
  }
]
```

**200:** `[]` if the perfume exists with no offers. **404:** Perfume not found.

### 6.2 GET `/api/retailers/<int:retailer_id>/offers`

Returns offers from the retailer joined with perfume attributes (`perfume_brand`, `perfume_name`, `perfume_concentration`), ordered by perfume brand, name, and offer volume.

**200** response (example shortened):

```json
[
  {
    "id": 7,
    "perfume_id": 1,
    "retailer_id": 1,
    "perfume_brand": "Frederic Malle",
    "perfume_name": "Musc Ravageur",
    "perfume_concentration": "EDP",
    "volume_ml": 100,
    "price_kzt": "168000.00",
    "product_url": "https://goldapple.kz/82401500003-musc-ravageur",
    "is_available": true,
    "checked_at": "Thu, 12 Nov 2026 10:00:00 GMT"
  }
]
```

**200:** `[]` if retailer exists but has no offers. **404:** Retailer not found.

### 6.3 GET `/api/perfumes/<int:perfume_id>/cheapest`

Find the cheapest available offer for the exact requested bottle size. Optional query `volume_ml` (positive integer, ASCII decimal digits). If omitted, defaults to `postgres_sabog_table.volume_ml`.

```http
GET /api/perfumes/1/cheapest?volume_ml=100
GET /api/perfumes/1/cheapest
```

**200** example:

```json
{
  "perfume_id": 1,
  "perfume_name": "Musc Ravageur",
  "perfume_brand": "Frederic Malle",
  "requested_volume_ml": 100,
  "cheapest_offer": {
    "id": 7,
    "perfume_id": 1,
    "retailer_id": 1,
    "retailer_name": "Golden Apple",
    "retailer_website": "https://goldapple.kz",
    "volume_ml": 100,
    "price_kzt": "168000.00",
    "product_url": "https://goldapple.kz/82401500003-musc-ravageur",
    "is_available": true,
    "checked_at": "Thu, 12 Nov 2026 10:00:00 GMT"
  }
}
```

Behavior:

1. Check perfume exists (404 if not).
2. Determine target volume from query or perfume record (400 for invalid/missing).
3. Filter `price_offers` by `perfume_id`, **equal `volume_ml`**, and `is_available = TRUE`.
4. Sort by `price_kzt ASC, id ASC`, take `LIMIT 1`.
5. Return 404 if no available matching offer exists.

**400:**

```json
{"error":"volume_ml must be a positive integer"}
```

**404:**

```json
{"error":"No available offers for this volume"}
```

## 7. End-to-end Postman demonstration

Import `postman/Perfume_Price_Tracker.postman_collection.json` and keep `baseUrl=http://localhost:5051`.

Run the folders **in this order**:

1. **01 Health:** Check API availability.
2. **02 Create Test Data:** POST test perfume → POST test retailer → POST test offer; scripts save IDs automatically.
3. **03 Perfumes:** List, read, update, and filter perfumes.
4. **04 Retailers:** List, read, update retailer.
5. **05 Price Offers:** List, read, update offer.
6. **06 Related:** Query offers by perfume, by retailer, and cheapest offer (with/without size).
7. **07 Negative Tests:** Request invalid/missing resources, negative price, duplicate offer, and invalid query inputs.
8. **08 Cleanup:** DELETE test offer → DELETE test retailer → DELETE test perfume.

**Do not point the cleanup requests at real IDs.** The collection uses `testPerfumeId`, `testRetailerId`, `testOfferId`, populated from the POST responses rather than hard-coded to `1`.

## 8. Testing and safety notes

- CRUD and join operations have been manually tested in Postman during development. This collection additionally includes status-code assertions and sample negative tests; run it against your own running local containers before submission to record a final green result.
- The test store uses `example.com` as a deliberately fictitious address; its prices are test values, not live market data.
- `DELETE /api/perfumes/<id>` cascades to `price_offers`; therefore the cleanup deletes the test offer first, then retailer, then perfume.
- No scheduled scraping, price update automation, decant pricing, or historical pricing is included in this mandatory submission.
