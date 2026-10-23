
from database import Base, engine

Base.metadata.create_all(bind=engine)

print("CardioTrack database and tables created successfully!")
