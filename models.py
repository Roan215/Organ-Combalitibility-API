from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float
from sqlalchemy.orm import relationship

from db import Base

class Person(Base):
    __tablename__ = 'person'
    id = Column(Integer, primary_key=True,index=True)
    name = Column(String,index=True)
    age= Column(Integer,index=True)
    gender = Column(String,index=True)
    blood_type= Column(String,index=True)
    hla_typing= Column(String,index=True)
    infection_status=Column(Boolean,default=False,index=True)

    organ_size = relationship("OrganSize", back_populates="person", uselist=False)
    organ_status = relationship("OrganStatus", back_populates="person", uselist=False)

class OrganSize(Base):
    __tablename__ = 'organ_size'
    id = Column(Integer, primary_key=True,index=True)
    kidney_volume= Column(Float,index=True)
    liver_volume= Column(Float,index=True)
    heart_volume= Column(Float,index=True)
    single_lung_volume= Column(Float,index=True)
    pancreas_size=Column(Float,index=True)
    intestine_volume= Column(Float,index=True)
    person_id=Column(Integer, ForeignKey('person.id'))

    person = relationship("Person", back_populates="organ_size")

class OrganStatus(Base):
    __tablename__ = 'organ_status'
    id = Column(Integer, primary_key=True,index=True)
    corenea=Column(Boolean,default=True,index=True)
    kidney=Column(Boolean,default=True,index=True)
    liver=Column(Boolean,default=True,index=True)
    heart=Column(Boolean,default=True,index=True)
    lungs=Column(Boolean,default=True,index=True)
    pancreas=Column(Boolean,default=True,index=True)
    intestine=Column(Boolean,default=True,index=True)
    person_id=Column(Integer, ForeignKey('person.id'))

    person = relationship("Person", back_populates="organ_status")

