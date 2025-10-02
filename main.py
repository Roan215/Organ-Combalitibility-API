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
    corenea: bool
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


@app.get("/availabillity/{organ}")
async def availabeList(organ:str,db: db_dependency):
    if not hasattr(models.OrganStatus,organ):
        raise HTTPException(status_code=404, detail="Organ not found")

    column_attr=getattr(models.OrganStatus,organ)

    if not isinstance(column_attr.type,Boolean):
        raise HTTPException(status_code=404, detail="Organ not found")

    results = (
        db.query(models.Person)
        .join(models.OrganStatus)
        .filter(column_attr == True)
        .all()
    )
    return results


@app.post("/compatibility/{id}")
async def compatibility(
    id: int,
    person: PersonDetails,
    organ: str = Query(..., description="Organ to check (e.g., kidney, liver, heart)"),
    db: Session = Depends(get_db),
):
    # Fetch donor with organ sizes and status
    donor = (
        db.query(models.Person)
          .filter(models.Person.id == id)
          .first()
    )

    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")

    # 1. Donor must be infection free
    if donor.infection_status:
        return {"compatible": False, "reason": "Donor has infection"}

    # 2. Gender, blood type, HLA must match
    if donor.gender != person.person.gender:
        return {"compatible": False, "reason": "Gender mismatch"}
    if donor.blood_type != person.person.blood_type:
        return {"compatible": False, "reason": "Blood type mismatch"}
    if donor.hla_typing != person.person.hla_typing:
        return {"compatible": False, "reason": "HLA typing mismatch"}

    # 3. Age difference <= 10
    if abs(donor.age - person.person.age) > 10:
        return {"compatible": False, "reason": "Age difference too large"}

    # 4. Check requested organ availability
    donor_status = donor.organ_status
    if not getattr(donor_status, organ, False):
        return {"compatible": False, "reason": f"Donor does not have {organ} available"}

    # 5. Compare organ size
    donor_size = donor.organ_size
    person_size = person.organ_size

    donor_value = getattr(donor_size, f"{organ}_volume", None)
    person_value = getattr(person.organ_size, f"{organ}_volume", None)

    if donor_value is None or person_value is None:
        raise HTTPException(status_code=400, detail=f"Invalid organ '{organ}'")

    # Allow exact match (or could add tolerance)
    if donor_value != person_value:
        return {"compatible": False, "reason": f"{organ.capitalize()} size mismatch"}

    # ✅ All checks passed
    return {"compatible": True, "reason": f"Donor is compatible for {organ}"}