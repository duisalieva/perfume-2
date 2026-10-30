import os
import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"]
    )


def init_db():
    connection = get_connection()

    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS postgres_sabog_table (
                        id SERIAL PRIMARY KEY,
                        brand VARCHAR(100) NOT NULL,
                        name VARCHAR(150) NOT NULL,
                        concentration VARCHAR(30),
                        volume_ml INTEGER CHECK (volume_ml > 0),
                        remaining_ml INTEGER CHECK (remaining_ml >= 0),
                        top_notes TEXT,
                        heart_notes TEXT,
                        base_notes TEXT,
                        fragrance_family VARCHAR(100),
                        status VARCHAR(20) NOT NULL
                            CHECK (status IN ('owned', 'wishlist', 'want_to_test')),

                        CHECK (
                            remaining_ml IS NULL
                            OR (
                                volume_ml IS NOT NULL
                                AND remaining_ml <= volume_ml
                            )
                        ),

                        CHECK (
                            status = 'owned'
                            OR remaining_ml IS NULL
                        )
                    );
                """)
    finally:
        connection.close()