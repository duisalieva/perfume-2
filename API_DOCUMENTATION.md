# My Perfume Collection — REST API Documentation

**Base URL:** `http://localhost:5051`  
**Content type for POST / PUT:** `application/json`  
**Database:** PostgreSQL (`postgres_sabog_db`, table `postgres_sabog_table`)

All examples show JSON sent to or returned by the Flask backend. IDs in the examples are illustrative: PostgreSQL assigns them automatically, so IDs may have gaps.

## Data model

| Field | Type | Required for POST/PUT? | Validation |
| --- | --- | --- | --- |
| `id` | integer | No | Assigned automatically by PostgreSQL |
| `brand` | string | Yes | Non-empty, up to 100 characters in database |
| `name` | string | Yes | Non-empty, up to 150 characters in database |
| `concentration` | string/null | No | String if provided; database max 30 characters |
| `volume_ml` | integer/null | No | Positive integer if provided |
| `remaining_ml` | integer/null | No | Non-negative; requires `status=owned`, valid `volume_ml`, and `remaining_ml <= volume_ml` |
| `top_notes` | string/null | No | String if provided |
| `heart_notes` | string/null | No | String if provided |
| `base_notes` | string/null | No | String if provided |
| `fragrance_family` | string/null | No | String if provided; database max 100 characters |
| `status` | string | Yes | Exactly `owned`, `wishlist`, or `want_to_test` |

**Note:** `PUT` uses a full-record update. The API requires `brand`, `name`, and `status`. Optional fields omitted from a PUT request become `null` in the stored row.

## 1. Health check

**Request:** `GET /api/health`

**Response — 200 OK**

```json
{
  "project": "My Perfume Collection",
  "status": "ok"
}
```

This endpoint confirms that Flask is responding. It does not directly query PostgreSQL.

## 2. List all perfumes

**Request:** `GET /api/perfumes`

**Response — 200 OK**

```json
[
  {
    "id": 1,
    "brand": "Frederic Malle",
    "name": "Musc Ravageur",
    "concentration": "EDP",
    "volume_ml": 100,
    "remaining_ml": 90,
    "top_notes": "Lavender, Tangerine, Bergamot, Coriander, Neroli",
    "heart_notes": "Cinnamon, Cloves, Orris Root, Rose, Osmanthus",
    "base_notes": "Musk, Vanilla, Tonka Bean, Amber, Sandalwood, Guaiac Wood, Cedar, Animal notes, Patchouli",
    "fragrance_family": "Oriental Spicy",
    "status": "owned"
  }
]
```

If the database contains no perfumes, the response is the empty array `[]`. Results are ordered by `id`.

### Optional filters

| Parameter | Accepted values | Behavior |
| --- | --- | --- |
| `status` | `owned`, `wishlist`, `want_to_test` | Return only perfumes with the selected status |
| `low_stock` | `true`, `false` | If `true`, also require `status='owned'` and `remaining_ml <= 10`. If `false`, do not add a low-stock restriction. |

Examples:

```http
GET /api/perfumes?status=wishlist
GET /api/perfumes?status=owned&low_stock=true
GET /api/perfumes?low_stock=true
```

**Invalid filter — 400 Bad Request**

```json
{"error": "Invalid status"}
```

or

```json
{"error": "low_stock must be true or false"}
```

When both filters are present, their conditions are combined with SQL `AND`.

## 3. Get perfume by ID

**Request:** `GET /api/perfumes/1`

The final path segment is the integer ID of the perfume.

**Response — 200 OK:** a single perfume object with the fields listed above.

**Response — 404 Not Found:**

```json
{"error": "Perfume not found"}
```

## 4. Create perfume

**Request:** `POST /api/perfumes`  
**Header:** `Content-Type: application/json`

**Example body:**

```json
{
  "brand": "Test Brand",
  "name": "API Test Perfume - safe to delete",
  "concentration": "EDP",
  "volume_ml": 30,
  "remaining_ml": 15,
  "top_notes": "Bergamot",
  "heart_notes": "Rose",
  "base_notes": "Musk",
  "fragrance_family": "Floral",
  "status": "owned"
}
```

**Response — 201 Created:** the created record, including its new `id` and all stored fields.

Example:

```json
{
  "id": 4,
  "brand": "Test Brand",
  "name": "API Test Perfume - safe to delete",
  "concentration": "EDP",
  "volume_ml": 30,
  "remaining_ml": 15,
  "top_notes": "Bergamot",
  "heart_notes": "Rose",
  "base_notes": "Musk",
  "fragrance_family": "Floral",
  "status": "owned"
}
```

**Possible 400 Bad Request responses:**

```json
{"error": "JSON object required"}
```

```json
{"error": "brand is required"}
```

```json
{"error": "Invalid status"}
```

```json
{"error": "Invalid volume_ml"}
```

```json
{"error": "Invalid remaining_ml"}
```

```json
{"error": "Only owned perfumes can have remaining_ml"}
```

```json
{"error": "Remaining volume cannot exceed total volume"}
```

For non-text optional string fields, the API also reports `<field> must be text`. Some database constraints (such as VARCHAR length limits) are enforced by PostgreSQL itself.

## 5. Update perfume by ID

**Request:** `PUT /api/perfumes/4`  
**Header:** `Content-Type: application/json`

Send the **full set of intended fields**. `brand`, `name`, and `status` must be provided; optional fields omitted from the request are saved as `null`.

**Example body:**

```json
{
  "brand": "Test Brand",
  "name": "API Test Perfume - safe to delete",
  "concentration": "EDP",
  "volume_ml": 30,
  "remaining_ml": 7,
  "top_notes": "Bergamot",
  "heart_notes": "Rose",
  "base_notes": "Musk",
  "fragrance_family": "Floral",
  "status": "owned"
}
```

**Response — 200 OK:** the updated perfume object (`remaining_ml` will now be `7` in this example).

**Response — 404 Not Found:**

```json
{"error": "Perfume not found"}
```

**Response — 400 Bad Request:** request validation errors follow the same rules as POST.

## 6. Delete perfume by ID

**Request:** `DELETE /api/perfumes/4`

**Response — 200 OK:**

```json
{
  "message": "Perfume deleted successfully",
  "id": 4
}
```

**Response — 404 Not Found:**

```json
{"error": "Perfume not found"}
```

**Caution:** DELETE permanently removes the selected perfume from the database. For demonstration, first create a temporary test perfume and use its actual returned ID.

## Postman demonstration sequence

1. `GET /api/health` — expect `200`.
2. `GET /api/perfumes` — expect `200` and an array.
3. `POST /api/perfumes` — create a temporary test perfume; expect `201`; copy its actual `id`.
4. Set the Postman collection variable `perfumeId` to that ID manually.
5. `GET /api/perfumes/{{perfumeId}}` — expect `200`.
6. `PUT /api/perfumes/{{perfumeId}}` — expect `200`; update `remaining_ml` from `15` to `7`.
7. `GET /api/perfumes?status=owned` and `GET /api/perfumes?low_stock=true` — expect `200`.
8. `DELETE /api/perfumes/{{perfumeId}}` — expect `200`.
9. `GET /api/perfumes/{{perfumeId}}` — expect `404` after deletion.

The accompanying exported Postman Collection contains these saved requests; it does not require JavaScript scripts.
