from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Call(Base):
    __tablename__ = 'calls'

    id = Column(Integer, primary_key=True)
    file_name = Column(String(250), nullable=False)
    transcription = Column(Text)
    assigned_roles = Column(Text)

    def to_dict(self):
        return {
            'id': self.id,
            'file_name': self.file_name,
            'transcription': self.transcription,
            'assigned_roles': self.assigned_roles
        }