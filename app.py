from flask import Flask, jsonify, request #фласк для того, чтобы выполнять действия, jsonify возвращает инфу в формате джсон, request - как бы на иинпут помогает получать данные для фласка
from psycopg2.extras import RealDictCursor #псай нужен чтобы выполнять запросы постгрес
from db import get_connection, init_db #методы из файла бд, чтобы подключаться к бд
from urllib.parse import urlsplit
from psycopg2.errors import UniqueViolation, ForeignKeyViolation
from decimal import Decimal, InvalidOperation


app = Flask(__name__) #переменная к которой будем обращаться чтобы работать


@app.route("/api/health", methods=["GET"]) #метод гет возвратит нам строчки указанные ниже в формате джсон
def health():
    return jsonify({
        "status": "ok",
        "project": "My Perfume Collection"
    })

# МЕТОД ГЕТ (ПРОСТО получаем всю таблицу)
@app.route("/api/perfumes", methods=["GET"])
def get_perfumes():

    status = request.args.get("status") #request это метод из фласка, тут он возвратит нам статус
    low_stock = request.args.get("low_stock") 

    if status is not None: #если статус вообще есть
        if status not in ["owned", "wishlist", "want_to_test"]: # но статус не из перечисленных 
            return jsonify({"error": "Invalid status"}), 400 #то ошибка

    if low_stock is not None: #почему тоо этот лоу сток должен быть либо тру либо фолс
        if low_stock not in ["true", "false"]:
            return jsonify({"error": "low_stock must be true or false"}), 400

    query = "SELECT * FROM postgres_sabog_table WHERE TRUE" # создаем сразу запрос, где есть условие (если условие ТРУ, то возвращаем всю таблицу где это условие выполняется)
    params = []

    if status is not None: # если статус вообще есть 
        query += " AND status = %s" #то получилось что query у нас "SELECT * FROM postgres_sabog_table WHERE TRUE  AND status = %s - где %s это пока placeholder "
        params.append(status) # тут добавляем в параметры статус

    if low_stock == "true":  # опять этот лоу сток и если он тру
        query += " AND status = 'owned' AND remaining_ml <= %s" #то тогда добавляем к прошлому или позапрошлому (в зависимости от того, был статус или нет)
        # может короче в наш query еще добавиться условие про то что оставшиеся милиллитры меньше пока плейсхолдера И обязательно статус owned, потому что 
        # мы позволяем оставаться духам только НАШИМ (логично)
        params.append(30) #зачем то теперь в параметрах еще и число 10

    query += " ORDER BY id" #еще в конце (по правилам скл) добавляем сортировку по айди

    connection = get_connection() #получаем данные по поводу логинов паролей хостов и тд

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params) # закидываем получившийся запрос и параметры (они я так полагаю встанут на место %s по порядку)

            perfumes = cursor.fetchall() #закидываем ВСЕ в переменную

        return jsonify(perfumes), 200 #переменная возвращает все и статус 200

    finally:
        connection.close()

#МЕТОД ПОСТ (заПОСТить:)

@app.route("/api/perfumes", methods=["POST"])
def create_perfume():

    # получаем данные из постмана 
    
    data = request.get_json(silent=True)
    # если пусто то ошибка
    if not isinstance(data, dict):  # isinstance(data, dict) если data в формате dict, то true
        return jsonify({"error": "JSON object required"}), 400

    # если нет этих полей то ошибка
    for field in ["brand", "name"]:
        if not isinstance(data.get(field), str) or not data[field].strip():
            return jsonify({"error": f"{field} is required"}), 400

    # если нет статуса то ошибка
    status = data.get("status")

    if status not in ["owned", "wishlist", "want_to_test"]:
        return jsonify({"error": "Invalid status"}), 400

    # проверим обьемы
    volume = data.get("volume_ml")
    remaining = data.get("remaining_ml")

    if volume is not None: #если обьем вообще УКАЗАН
        if type(volume) is not int or volume <= 0: #если тип данных не интеджер и если отрицательный то ОШИБКА
            return jsonify({"error": "Invalid volume_ml"}), 400

    if remaining is not None:
        if type(remaining) is not int or remaining < 0: 
            return jsonify({"error": "Invalid remaining_ml"}), 400

        if status != "owned": #позволяем только нашим парфюмам иметь остаток что логично хах
            return jsonify({"error": "Only owned perfumes can have remaining_ml"}), 400

        if volume is None or remaining > volume: 
            return jsonify({"error": "Remaining volume cannot exceed total volume"}), 400

    #  остались необязательные поля
    text_fields = [
        "concentration", "top_notes", "heart_notes",
        "base_notes", "fragrance_family"
    ]

    for field in text_fields:
        if data.get(field) is not None and not isinstance(data[field], str): #если в поле вообще что то есть но это не буквы то ошибка
            return jsonify({"error": f"{field} must be text"}), 400

    # подключаемся к постгрес
    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                
                cursor.execute("""
                    INSERT INTO postgres_sabog_table (
                        brand,
                        name,
                        concentration,
                        volume_ml,
                        remaining_ml,
                        top_notes,
                        heart_notes,
                        base_notes,
                        fragrance_family,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                    RETURNING *
                """, (
                    data["brand"].strip(),
                    data["name"].strip(),
                    data.get("concentration"),
                    volume,
                    remaining,
                    data.get("top_notes"),
                    data.get("heart_notes"),
                    data.get("base_notes"),
                    data.get("fragrance_family"),
                    status
                ))

                
                perfume = cursor.fetchone() 

        # 9. Возвращаем результат
        return jsonify(perfume), 201

    finally:
        connection.close()

# МЕТОД ГЕТ по АЙДИшке
@app.route("/api/perfumes/<int:perfume_id>", methods=["GET"])
def get_perfume(perfume_id):

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute(
                "SELECT * FROM postgres_sabog_table WHERE id = %s",
                (perfume_id,)
            )

            perfume = cursor.fetchone()

        if perfume is None:
            return jsonify({"error": "Perfume not found"}), 404

        return jsonify(perfume), 200

    finally:
        connection.close()


# МЕТОД ПУТ !
@app.route("/api/perfumes/<int:perfume_id>", methods=["PUT"]) #тут мы в пути всегда будем указывать по какому именно айди мы должны положить инфу
#поэтому мы забираем ее как <int:perfume_id> и сразу как бы присваиваем переменной perfume_id полученный айди
def update_perfume(perfume_id): #тут сразу передаем айдишку

    data = request.get_json(silent=True) #тут понятно, чтобы нам не возвратили ошибки и не поломали, а мы пошли дальше и сами обозначили эти ошибки

    if not isinstance(data, dict): #если инфа не в формате словаря то ошибка
        return jsonify({"error": "JSON object required"}), 400

    for field in ["brand", "name"]:
        if not isinstance(data.get(field), str) or not data[field].strip(): #тут тоже если в этих столбцах дата не стринг или пустая то ошибка
            return jsonify({"error": f"{field} is required"}), 400

    status = data.get("status")

    if status not in ["owned", "wishlist", "want_to_test"]: #если статус не перечисленный то ошибка
        return jsonify({"error": "Invalid status"}), 400

    volume = data.get("volume_ml") #получаем данные об обьеме
    remaining = data.get("remaining_ml") # и об оставшемся обьеме

    if volume is not None:
        if type(volume) is not int or volume <= 0:
            return jsonify({"error": "Invalid volume_ml"}), 400 #обычные проверки как при пост методе

    if remaining is not None:
        if type(remaining) is not int or remaining < 0:
            return jsonify({"error": "Invalid remaining_ml"}), 400

        if status != "owned":
            return jsonify({
                "error": "Only owned perfumes can have remaining_ml"
            }), 400

        if volume is None or remaining > volume:
            return jsonify({
                "error": "Remaining volume cannot exceed total volume"
            }), 400

    text_fields = [
        "concentration",
        "top_notes",
        "heart_notes",
        "base_notes",
        "fragrance_family"
    ]

    for field in text_fields:
        if data.get(field) is not None and not isinstance(data[field], str):
            return jsonify({"error": f"{field} must be text"}), 400

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    UPDATE postgres_sabog_table
                    SET
                        brand = %s,
                        name = %s,
                        concentration = %s,
                        volume_ml = %s,
                        remaining_ml = %s,
                        top_notes = %s,
                        heart_notes = %s,
                        base_notes = %s,
                        fragrance_family = %s,
                        status = %s
                    WHERE id = %s
                    RETURNING *
                """, (
                    data["brand"].strip(), 
                    data["name"].strip(),
                    data.get("concentration"),
                    volume,
                    remaining,
                    data.get("top_notes"),
                    data.get("heart_notes"),
                    data.get("base_notes"),
                    data.get("fragrance_family"),
                    status,
                    perfume_id
                ))

                perfume = cursor.fetchone()

        if perfume is None:
            return jsonify({"error": "Perfume not found"}), 404

        return jsonify(perfume), 200

    finally:
        connection.close()
# короче в предыдушем методе все как в пост, только по айдишке, она не присваивается сама


# МЕТОД ДЕлит :(((
@app.route("/api/perfumes/<int:perfume_id>", methods=["DELETE"]) #тут все также как и раньше - нужно получиться айди 
def delete_perfume(perfume_id):

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    DELETE FROM postgres_sabog_table 
                    WHERE id = %s
                    RETURNING id
                """, (perfume_id,))
#вот здесь я прям вижу передачу айдишки за место %s
                deleted = cursor.fetchone()

        if deleted is None:
            return jsonify({"error": "Perfume not found"}), 404

        return jsonify({
            "message": "Perfume deleted successfully",
            "id": perfume_id
        }), 200

    finally:
        connection.close()

    # Validate retailer data
def validate_retailer_data():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, "JSON object required"

    name = data.get("name")
    website_url = data.get("website_url")

    # Validate retailer name
    if not isinstance(name, str) or not name.strip():
        return None, "Retailer name is required"

    name = name.strip()

    if len(name) > 150:
        return None, "Retailer name is too long"

    # Validate website URL
    if not isinstance(website_url, str) or not website_url.strip():
        return None, "Website URL is required"

    website_url = website_url.strip()

    try:
        parsed_url = urlsplit(website_url)

        if parsed_url.scheme not in ["http", "https"] or not parsed_url.hostname:
            return None, "Invalid website URL"

    except ValueError:
        return None, "Invalid website URL"

    return {
        "name": name,
        "website_url": website_url
    }, None

# GET all retailers
@app.route("/api/retailers", methods=["GET"])
def get_retailers():

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute("""
                SELECT *
                FROM retailers
                ORDER BY id
            """)

            retailers = cursor.fetchall()

        return jsonify(retailers), 200

    finally:
        connection.close()

# GET retailer by ID
@app.route("/api/retailers/<int:retailer_id>", methods=["GET"])
def get_retailer(retailer_id):

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute("""
                SELECT *
                FROM retailers
                WHERE id = %s
            """, (retailer_id,))

            retailer = cursor.fetchone()

        if retailer is None:
            return jsonify({"error": "Retailer not found"}), 404

        return jsonify(retailer), 200

    finally:
        connection.close()

# POST create retailer
@app.route("/api/retailers", methods=["POST"])
def create_retailer():

    data, error = validate_retailer_data()

    if error:
        return jsonify({"error": error}), 400

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    INSERT INTO retailers (name, website_url)
                    VALUES (%s, %s)
                    RETURNING *
                """, (
                    data["name"],
                    data["website_url"]
                ))

                retailer = cursor.fetchone()

        return jsonify(retailer), 201

    except UniqueViolation:
        return jsonify({
            "error": "Retailer with this name already exists"
        }), 409

    finally:
        connection.close()

# PUT update retailer
@app.route("/api/retailers/<int:retailer_id>", methods=["PUT"])
def update_retailer(retailer_id):

    data, error = validate_retailer_data()

    if error:
        return jsonify({"error": error}), 400

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    UPDATE retailers
                    SET
                        name = %s,
                        website_url = %s
                    WHERE id = %s
                    RETURNING *
                """, (
                    data["name"],
                    data["website_url"],
                    retailer_id
                ))

                retailer = cursor.fetchone()

        if retailer is None:
            return jsonify({"error": "Retailer not found"}), 404

        return jsonify(retailer), 200

    except UniqueViolation:
        return jsonify({
            "error": "Retailer with this name already exists"
        }), 409

    finally:
        connection.close()

# DELETE retailer
@app.route("/api/retailers/<int:retailer_id>", methods=["DELETE"])
def delete_retailer(retailer_id):

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    DELETE FROM retailers
                    WHERE id = %s
                    RETURNING id
                """, (retailer_id,))

                deleted = cursor.fetchone()

        if deleted is None:
            return jsonify({"error": "Retailer not found"}), 404

        return jsonify({
            "message": "Retailer deleted successfully",
            "id": retailer_id
        }), 200

    except ForeignKeyViolation:
        return jsonify({
            "error": "Cannot delete retailer with existing price offers"
        }), 409

    finally:
        connection.close()

# Validate price offer data
def validate_price_offer_data():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return None, "JSON object required"

    # Validate IDs and volume
    for field in ["perfume_id", "retailer_id", "volume_ml"]:

        value = data.get(field)

        if type(value) is not int or value <= 0:
            return None, f"{field} must be a positive integer"

    # Validate price
    raw_price = data.get("price_kzt")

    if type(raw_price) not in (int, float):
        return None, "price_kzt must be a number"

    try:
        price = Decimal(str(raw_price))

        if (
            not price.is_finite()
            or price <= 0
            or price > Decimal("9999999999.99")
        ):
            return None, "Invalid price_kzt"

        if price != price.quantize(Decimal("0.01")):
            return None, "price_kzt can have at most 2 decimal places"

    except (InvalidOperation, ValueError):
        return None, "Invalid price_kzt"

    # Validate product URL
    product_url = data.get("product_url")

    if not isinstance(product_url, str) or not product_url.strip():
        return None, "Product URL is required"

    product_url = product_url.strip()

    try:
        parsed_url = urlsplit(product_url)

        if (
            parsed_url.scheme not in ("http", "https")
            or not parsed_url.hostname
        ):
            return None, "Invalid product URL"

    except ValueError:
        return None, "Invalid product URL"

    # Validate availability
    is_available = data.get("is_available", True)

    if not isinstance(is_available, bool):
        return None, "is_available must be boolean"

    return {
        "perfume_id": data["perfume_id"],
        "retailer_id": data["retailer_id"],
        "volume_ml": data["volume_ml"],
        "price_kzt": str(price),
        "product_url": product_url,
        "is_available": is_available
    }, None
# GET all price offers
@app.route("/api/price-offers", methods=["GET"])
def get_price_offers():

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute("""
                SELECT *
                FROM price_offers
                ORDER BY id
            """)

            offers = cursor.fetchall()

        return jsonify(offers), 200

    finally:
        connection.close()

# GET price offer by ID
@app.route("/api/price-offers/<int:offer_id>", methods=["GET"])
def get_price_offer(offer_id):

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            cursor.execute("""
                SELECT *
                FROM price_offers
                WHERE id = %s
            """, (offer_id,))

            offer = cursor.fetchone()

        if offer is None:
            return jsonify({
                "error": "Price offer not found"
            }), 404

        return jsonify(offer), 200

    finally:
        connection.close()


# POST create price offer
@app.route("/api/price-offers", methods=["POST"])
def create_price_offer():

    data, error = validate_price_offer_data()

    if error:
        return jsonify({"error": error}), 400

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    INSERT INTO price_offers (
                        perfume_id,
                        retailer_id,
                        volume_ml,
                        price_kzt,
                        product_url,
                        is_available
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    data["perfume_id"],
                    data["retailer_id"],
                    data["volume_ml"],
                    data["price_kzt"],
                    data["product_url"],
                    data["is_available"]
                ))

                offer = cursor.fetchone()

        return jsonify(offer), 201

    except ForeignKeyViolation:
        return jsonify({
            "error": "Perfume or retailer does not exist"
        }), 400

    except UniqueViolation:
        return jsonify({
            "error": "Price offer already exists for this perfume, retailer and volume"
        }), 409

    finally:
        connection.close()

# PUT update price offer
@app.route("/api/price-offers/<int:offer_id>", methods=["PUT"])
def update_price_offer(offer_id):

    data, error = validate_price_offer_data()

    if error:
        return jsonify({"error": error}), 400

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    UPDATE price_offers
                    SET
                        perfume_id = %s,
                        retailer_id = %s,
                        volume_ml = %s,
                        price_kzt = %s,
                        product_url = %s,
                        is_available = %s,
                        checked_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING *
                """, (
                    data["perfume_id"],
                    data["retailer_id"],
                    data["volume_ml"],
                    data["price_kzt"],
                    data["product_url"],
                    data["is_available"],
                    offer_id
                ))

                offer = cursor.fetchone()

        if offer is None:
            return jsonify({
                "error": "Price offer not found"
            }), 404

        return jsonify(offer), 200

    except ForeignKeyViolation:
        return jsonify({
            "error": "Perfume or retailer does not exist"
        }), 400

    except UniqueViolation:
        return jsonify({
            "error": "Price offer already exists for this perfume, retailer and volume"
        }), 409

    finally:
        connection.close()

# DELETE price offer
@app.route("/api/price-offers/<int:offer_id>", methods=["DELETE"])
def delete_price_offer(offer_id):

    connection = get_connection()

    try:
        with connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:

                cursor.execute("""
                    DELETE FROM price_offers
                    WHERE id = %s
                    RETURNING id
                """, (offer_id,))

                deleted = cursor.fetchone()

        if deleted is None:
            return jsonify({
                "error": "Price offer not found"
            }), 404

        return jsonify({
            "message": "Price offer deleted successfully",
            "id": offer_id
        }), 200

    finally:
        connection.close()

# GET all offers for a specific perfume
@app.route("/api/perfumes/<int:perfume_id>/offers", methods=["GET"])
def get_perfume_offers(perfume_id):

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Check if perfume exists
            cursor.execute("""
                SELECT id
                FROM postgres_sabog_table
                WHERE id = %s
            """, (perfume_id,))

            if cursor.fetchone() is None:
                return jsonify({
                    "error": "Perfume not found"
                }), 404

            # Get offers with retailer information
            cursor.execute("""
                SELECT
                    po.*,
                    r.name AS retailer_name,
                    r.website_url AS retailer_website
                FROM price_offers po
                JOIN retailers r
                    ON po.retailer_id = r.id
                WHERE po.perfume_id = %s
                ORDER BY po.volume_ml, po.price_kzt
            """, (perfume_id,))

            offers = cursor.fetchall()

        return jsonify(offers), 200

    finally:
        connection.close()

# GET all offers from a specific retailer
@app.route("/api/retailers/<int:retailer_id>/offers", methods=["GET"])
def get_retailer_offers(retailer_id):

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Check if retailer exists
            cursor.execute("""
                SELECT id
                FROM retailers
                WHERE id = %s
            """, (retailer_id,))

            if cursor.fetchone() is None:
                return jsonify({
                    "error": "Retailer not found"
                }), 404

            # Get offers with perfume information
            cursor.execute("""
                SELECT
                    po.*,
                    p.brand AS perfume_brand,
                    p.name AS perfume_name,
                    p.concentration AS perfume_concentration
                FROM price_offers po
                JOIN postgres_sabog_table p
                    ON po.perfume_id = p.id
                WHERE po.retailer_id = %s
                ORDER BY p.brand, p.name, po.volume_ml
            """, (retailer_id,))

            offers = cursor.fetchall()

        return jsonify(offers), 200

    finally:
        connection.close()

# GET cheapest available offer for a perfume
@app.route("/api/perfumes/<int:perfume_id>/cheapest", methods=["GET"])
def get_cheapest_offer(perfume_id):

    connection = get_connection()

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:

            # Get perfume and its original volume
            cursor.execute("""
                SELECT id, brand, name, volume_ml
                FROM postgres_sabog_table
                WHERE id = %s
            """, (perfume_id,))

            perfume = cursor.fetchone()

            if perfume is None:
                return jsonify({
                    "error": "Perfume not found"
                }), 404

            # Optional volume filter
            requested_volume = request.args.get("volume_ml")

            if requested_volume is not None:

                if (
                    not requested_volume.isascii()
                    or not requested_volume.isdecimal()
                    or int(requested_volume) <= 0
                ):
                    return jsonify({
                        "error": "volume_ml must be a positive integer"
                    }), 400

                volume_ml = int(requested_volume)

            else:
                # By default compare the same bottle size
                volume_ml = perfume["volume_ml"]

            if volume_ml is None or volume_ml <= 0:
                return jsonify({
                    "error": "Specify a valid volume_ml"
                }), 400

            # Find the cheapest available offer
            cursor.execute("""
                SELECT
                    po.*,
                    r.name AS retailer_name,
                    r.website_url AS retailer_website
                FROM price_offers po
                JOIN retailers r
                    ON po.retailer_id = r.id
                WHERE
                    po.perfume_id = %s
                    AND po.volume_ml = %s
                    AND po.is_available = TRUE
                ORDER BY po.price_kzt ASC, po.id ASC
                LIMIT 1
            """, (perfume_id, volume_ml))

            cheapest = cursor.fetchone()

        if cheapest is None:
            return jsonify({
                "error": "No available offers for this volume"
            }), 404

        return jsonify({
            "perfume_id": perfume_id,
            "perfume_name": perfume["name"],
            "perfume_brand": perfume["brand"],
            "requested_volume_ml": volume_ml,
            "cheapest_offer": cheapest
        }), 200

    finally:
        connection.close()

if __name__ == "__main__":
    print("INITIALIZING SABOG's DATABASE", flush=True)
    init_db() 
    app.run(host="0.0.0.0", port=5051) #просто запускает то что мы написали выше