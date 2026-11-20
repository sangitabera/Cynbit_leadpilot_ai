from app.database.connection import Base, engine
from app.database.models import Lead


def initialize_database():
    Base.metadata.create_all(bind=engine)