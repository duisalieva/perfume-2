from flask import Flask, jsonify, request #фласк для того, чтобы выполнять действия, jsonify возвращает инфу в формате джсон, request - как бы на иинпут помогает получать данные для фласка
from psycopg2.extras import RealDictCursor #псай нужен чтобы выполнять запросы постгрес
from db import get_connection, init_db #методы из файла бд, чтобы подключаться к бд


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
    low_stock = request.args.get("low_stock") # возврат тех у кого low_stock?

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

    if remaining is not None: #если оставшийся обьем вообще УКАЗАН
        if type(remaining) is not int or remaining < 0: #то же самое, но тут может быть 0 мл
            return jsonify({"error": "Invalid remaining_ml"}), 400

        if status != "owned": #позволяем только нашим парфюмам иметь остаток что логично хах
            return jsonify({"error": "Only owned perfumes can have remaining_ml"}), 400

        if volume is None or remaining > volume: #если указан только оставшийся обьем или если оставшийся больше чем полный флакон то ОШИБКА
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

                # делаем инсерт постгрес
                # занимаем места в самолете с помощью (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) - так как где то есть текста, или странные названия лучше сделать так
                # RETURNING * значит вернуть все обратно после вставки данных
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

                # 8 снова забрали все после RETURNING *
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
# если в первом гете я все правильно поняла, то здесь все тоже так же 

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

    status = data.get("status") #сохраняем статус, но не очень понимаю где мы забрали perfume_id - просто же передали в функцию, но в теле функции пока не использовали?

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
#получается ВОТ ЗДЕСЬ только мы юзаем айдишку, а до этого использовали просто всю таблицу целиком? а статус получали из постмана
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



if __name__ == "__main__":
    print("INITIALIZING SABOG's DATABASE", flush=True)
    init_db() # создаем таблицу - мы ее создаем как шаблон что ли? у нас же есть CREATE TABLE IF NOT EXISTS postgres_sabog_table в db.py
    app.run(host="0.0.0.0", port=5051) #просто запускает то что мы написали выше