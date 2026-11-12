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
                            # Create retailers table
                        # Create retailers table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS retailers (
                        id SERIAL PRIMARY KEY,

                        name VARCHAR(150) NOT NULL UNIQUE,

                        website_url TEXT NOT NULL,

                        created_at TIMESTAMPTZ
                            NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                            # Create price offers table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS price_offers (
                        id SERIAL PRIMARY KEY,

                        perfume_id INTEGER NOT NULL
                            REFERENCES postgres_sabog_table(id)
                            ON DELETE CASCADE,

                        retailer_id INTEGER NOT NULL
                            REFERENCES retailers(id)
                            ON DELETE RESTRICT,

                        volume_ml INTEGER NOT NULL
                            CHECK (volume_ml > 0),

                        price_kzt NUMERIC(12, 2) NOT NULL
                            CHECK (price_kzt > 0),

                        product_url TEXT NOT NULL,

                        is_available BOOLEAN NOT NULL DEFAULT TRUE,

                        checked_at TIMESTAMPTZ
                            NOT NULL DEFAULT CURRENT_TIMESTAMP,

                        CONSTRAINT unique_price_offer
                            UNIQUE (perfume_id, retailer_id, volume_ml)
                    );
                """)
                              
                cursor.execute("""
                    INSERT INTO retailers (name, website_url)
                    VALUES
                        ('Golden Apple', 'https://goldapple.kz'),
                        ('Parfbar', 'https://parfbar.kz')
                    ON CONFLICT (name) DO NOTHING;
                """)
    finally:
        connection.close()