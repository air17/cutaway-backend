from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

HOST = "database-1.cnwmpgpuofh0.eu-central-1.rds.amazonaws.com"
PORT = "3306"
DB_NAME = "cutaway"
LOGIN = "cutaway"
PASSWORD = "Cutaway4321"
SQLALCHEMY_DATABASE_URL = f"mysql+mysqldb://{LOGIN}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, pool_recycle=3600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
