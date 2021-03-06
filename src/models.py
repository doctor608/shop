from dataclasses import dataclass

from passlib.context import CryptContext

from db import db

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    default="pbkdf2_sha256",
    pbkdf2_sha256__default_rounds=30000,
)


@dataclass
class Shop:
    id: int
    name: str
    slug: str
    image: str

    __table__ = 'shops'

    def get_categories(self):
        db.cursor.execute("""
            SELECT DISTINCT categories.id, categories.name, categories.image
            FROM categories

            INNER JOIN product_category
            ON product_category.category_id = categories.id

            INNER JOIN products
            ON products.id = product_category.product_id

            WHERE products.shop_id = %s
            ORDER BY categories.name;
        """, (self.id, ))
        rows = db.cursor.fetchall()
        db.conn.commit()
        categories = [Category(*row) for row in rows]
        return categories

    @classmethod
    def create(cls, name, slug, image=''):
        db.cursor.execute(f"""
            INSERT INTO {cls.__table__} (name, slug, image) VALUES (
                %s, %s, %s
            ) RETURNING *
        """, (name, slug, image))
        row = db.cursor.fetchone()
        db.conn.commit()
        return cls(*row)

    @classmethod
    def get(cls, pk=None, slug=None):
        if pk is not None:
            db.cursor.execute(f"""
                SELECT * FROM {cls.__table__} WHERE {cls.__table__}.id = %s
            """, (pk,))
        elif slug is not None:
            db.cursor.execute(f"""
                SELECT * FROM {cls.__table__} WHERE {cls.__table__}.slug = %s
            """, (slug,))
        else:
            raise ValueError(f'{cls.__name__}: Either pk or slug is required.')

        row = db.cursor.fetchone()
        db.conn.commit()

        return None if row is None else cls(*row)

    @classmethod
    def all(cls):
        db.cursor.execute(f"""
            SELECT * FROM {cls.__table__}
        """)
        rows = db.cursor.fetchall()
        db.conn.commit()
        shops = [cls(*row) for row in rows]
        return shops

    @property
    def products(self):
        db.cursor.execute("""
            SELECT * FROM products
            INNER JOIN shops ON shops.id = products.shop_id
            WHERE shop_id = %s
        """, (self.id, ))
        rows = db.cursor.fetchall()
        db.conn.commit()
        products = [Product(*row[:5], self.__class__(*row[6:])) for row
                    in rows]
        return products

    @property
    def reviews(self):
        db.cursor.execute("""
            SELECT * FROM shop_reviews
            WHERE shop_id = %s
        """, (self.id, ))
        rows = db.cursor.fetchall()
        db.conn.commit()
        reviews = [ShopReview(*row[:-1], self) for row in rows]
        return reviews

    def get_absolute_url(self):
        return f'/shops/{self.slug}'


@dataclass
class ShopReview:
    id: int
    username: str
    text: str
    shop: Shop

    @classmethod
    def create(cls, username, text, shop_id):
        db.cursor.execute("""
            INSERT INTO shop_reviews (
                username, text, shop_id) VALUES (
                %s, %s, %s
            ) RETURNING *
        """, (username, text, shop_id))
        row = db.cursor.fetchone()
        db.conn.commit()
        return cls(*row)


@dataclass
class Category:
    id: int
    name: str
    image: str

    __table__ = 'categories'

    @classmethod
    def create(cls, name, image=''):
        db.cursor.execute(f"""
            INSERT INTO {cls.__table__} (
                name, image) VALUES (
                %s, %s
            ) RETURNING *
        """, (name, image))
        row = db.cursor.fetchone()
        db.conn.commit()
        return cls(*row)

    @classmethod
    def all(cls):
        db.cursor.execute(f"""
            SELECT * FROM {cls.__table__}
        """)
        rows = db.cursor.fetchall()
        db.conn.commit()
        categories = [cls(*row) for row in rows]
        return categories

    @classmethod
    def get(cls, pk=None, name=None):
        if pk is not None:
            db.cursor.execute(f"""
                SELECT * FROM {cls.__table__} WHERE {cls.__table__}.id = %s
            """, (pk,))
        elif name is not None:
            db.cursor.execute(f"""
                SELECT * FROM {cls.__table__} WHERE {cls.__table__}.name = %s
            """, (name,))
        else:
            raise ValueError(f'{cls.__name__}: Either pk or name is required.')

        row = db.cursor.fetchone()
        db.conn.commit()

        return None if row is None else cls(*row)


@dataclass
class User:
    id: int
    username: str
    email: str
    password: str

    __table__ = 'users'

    @staticmethod
    def encrypt_password(password: str) -> str:
        return pwd_context.encrypt(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password)

    @classmethod
    def create(cls, username, email, password):
        db.cursor.execute(f"""
            INSERT INTO {cls.__table__} (
                username, email, password) VALUES (
                %s, %s, %s
            ) RETURNING *
        """, (username, email, User.encrypt_password(password)))
        row = db.cursor.fetchone()
        db.conn.commit()
        return cls(*row)

    @classmethod
    def check_unique(cls, username: str, email: str) -> bool:
        db.cursor.execute(f"""
            SELECT EXISTS(SELECT 1 FROM {cls.__table__} WHERE username = %s
            OR email = %s
        )
        """, (username, email))
        row = db.cursor.fetchone()
        db.conn.commit()
        return row[0] is False


@dataclass
class Product:
    id: int
    name: str
    price: float
    image: str
    description: str = ''
    shop: Shop = None

    __table__ = 'products'

    def get_categories(self):
        db.cursor.execute("""
            SELECT categories.id, categories.name, categories.image
            FROM product_category
            INNER JOIN categories ON
            categories.id = product_category.category_id
            WHERE product_id = %s
        """, (self.id, ))
        rows = db.cursor.fetchall()
        db.conn.commit()
        categories = [Category(*row) for row in rows]
        return categories

    def add_category(self, category_id):
        db.cursor.execute("""
            INSERT INTO product_category (
                product_id, category_id
            ) VALUES (%s, %s)
        """, (self.id, category_id))

    def update(self, name, price, description, image):
        db.cursor.execute(f"""
            UPDATE {self.__table__}
            SET name = %s,
                price = %s,
                description = %s,
                image = %s
            WHERE {self.__table__}.id = %s
            RETURNING *
        """, (name, price, description, image, self.id))
        row = db.cursor.fetchone()
        db.conn.commit()
        return self.__class__(*row[:6])

    @classmethod
    def get_by_shop_category(cls, shop_id, category_id):
        db.cursor.execute(f"""
            SELECT *
            FROM {cls.__table__}
            INNER JOIN product_category ON product_category.category_id = %s
            WHERE product_category.product_id = {cls.__table__}.id
            AND {cls.__table__}.shop_id = %s
        """, (category_id, shop_id))
        rows = db.cursor.fetchall()
        db.conn.commit()
        return [cls(*row[:6]) for row in rows]

    @classmethod
    def create(cls, name, price, shop_id, image='', description=''):
        db.cursor.execute(f"""
            INSERT INTO {cls.__table__} (
                name, price, shop_id, image, description) VALUES (
                %s, %s, %s, %s, %s
            ) RETURNING *
        """, (name, price, shop_id, image, description))
        row = db.cursor.fetchone()
        db.conn.commit()
        return cls(*row)

    def delete(self):
        db.cursor.execute(f"""
            DELETE FROM {self.__table__} WHERE {self.__table__}.id = %s
        """, (self.id,))
        db.conn.commit()

    @classmethod
    def get(cls, pk):
        db.cursor.execute(f"""
            SELECT * FROM {cls.__table__}
            INNER JOIN shops ON shops.id = {cls.__table__}.shop_id
            WHERE {cls.__table__}.id = %s
        """, (pk,))
        row = db.cursor.fetchone()
        db.conn.commit()
        return None if row is None else cls(*row[:5], Shop(*row[6:]))

    @classmethod
    def all(cls):
        db.cursor.execute(f"""
            SELECT * FROM {cls.__table__}
            INNER JOIN shops ON shops.id = {cls.__table__}.shop_id
        """)
        rows = db.cursor.fetchall()
        db.conn.commit()
        products = [cls(*row[:5], Shop(*row[6:])) for row in rows]
        return products
