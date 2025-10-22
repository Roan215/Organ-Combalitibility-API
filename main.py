from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List,Annotated
from sqlalchemy import Boolean
import models
from db import engine,SessionLocal
from sqlalchemy.orm import Session

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

class PersonBase(BaseModel):
    name: str
    age: int
    gender: str
    blood_type: str
    hla_typing: str
    infection_status: bool

class OrganSize(BaseModel):
    kidney_volume: float
    liver_volume: float
    heart_volume: float
    single_lung_volume: float
    pancreas_size: float
    intestine_volume: float

class OrganStatus(BaseModel):
    cornea: bool
    kidney: bool
    liver: bool
    heart: bool
    lungs: bool
    pancreas: bool
    intestine: bool

class PersonDetails(BaseModel):
    person: PersonBase
    organ_size: OrganSize
    organ_status: OrganStatus

class ReceiverInput(BaseModel):
    name: str
    age: int
    gender: str
    blood_type: str
    hla_typing: str
    infection_status: bool
    organ_size: float  # only one organ’s size

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session,Depends(get_db)]


@app.post("/add_person")
async def add_person(data: PersonDetails,db: db_dependency):
    db_person = models.Person(**data.person.dict())
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    id=db_person.id
    db_organ_size = models.OrganSize(**data.organ_size.dict(), person_id=db_person.id)
    db.add(db_organ_size)
    db.commit()
    db_organ_status = models.OrganStatus(**data.organ_status.dict(), person_id=db_person.id)
    db.add(db_organ_status)
    db.commit()


@app.get("/availability/{organ}")
async def availableList(organ: str, db: db_dependency):
    if not hasattr(models.OrganStatus, organ):
        raise HTTPException(status_code=404, detail="Organ not found")

    column_attr = getattr(models.OrganStatus, organ)

    if not isinstance(column_attr.type, Boolean):
        raise HTTPException(status_code=404, detail="Organ not found")

    results = (
        db.query(models.Person)
        .join(models.OrganStatus)
        .filter(column_attr == True)
        .all()
    )

    donor_list = []
    for person in results:
        donor_list.append({
            "id": person.id,
            "name": person.name,
            "age": person.age,
            "gender": person.gender,
            "blood_type": person.blood_type,
            "hla_typing": person.hla_typing,
            "infection_status": person.infection_status
        })

    return {
        "organ": organ,
        "total_donors": len(donor_list),
        "donors": donor_list
    }



@app.post("/compatibility/{id}/{organ}")
async def compatibility(
    id: int,
    organ: str,
    receiver: ReceiverInput,
    db: Session = Depends(get_db),
):
    donor = db.query(models.Person).filter(models.Person.id == id).first()
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")

    # 3. Organ availability check
    donor_status = donor.organ_status
    if not getattr(donor_status, organ, False):
        return {"compatible": False, "reason": f"Donor does not have {organ} available"}

    # 1. Donor infection check
    if donor.infection_status:
        return {"compatible": False, "reason": "Donor has infection"}

    # 2. Match common attributes
    if donor.gender != receiver.gender:
        return {"compatible": False, "reason": "Gender mismatch"}
    if donor.blood_type != receiver.blood_type:
        return {"compatible": False, "reason": "Blood type mismatch"}
    if donor.hla_typing != receiver.hla_typing:
        return {"compatible": False, "reason": "HLA typing mismatch"}
    if abs(donor.age - receiver.age) > 10:
        return {"compatible": False, "reason": "Age difference too large"}



    # 4. Compare organ size
    organ_size_fields = {
        "kidney": "kidney_volume",
        "liver": "liver_volume",
        "heart": "heart_volume",
        "lungs": "single_lung_volume",
        "pancreas": "pancreas_size",
        "intestine": "intestine_volume",
    }

    field_name = organ_size_fields.get(organ)
    if field_name:
        donor_size_value = getattr(donor.organ_size, field_name)
        receiver_size_value = receiver.organ_size
        if abs(donor_size_value - receiver_size_value) > 0.1 * receiver_size_value:
            return {"compatible": False, "reason": f"{organ.capitalize()} size mismatch"}

    return {"compatible": True, "reason": f"Donor is compatible for {organ}"}