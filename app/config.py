from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_USER = os.getenv("DATABASE_USER", "root")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "your_password")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
DATABASE_NAME = os.getenv("DATABASE_NAME", "your_db_name")
IS_DEBUG = os.getenv("IS_DEBUG", "False").lower() in ("true", "1", "t")
