from fastapi import APIRouter, HTTPException, Query
from ..services.validation import report

router=APIRouter()

@router.get('/validation')
def validation(rainfall_mm:float=Query(150,ge=0,le=250),top_n:int=Query(12,ge=1,le=500),
               radius_m:int=Query(300,ge=50,le=2000)):
    try: return report(rainfall_mm,top_n,radius_m)
    except (ValueError,FileNotFoundError) as e: raise HTTPException(400,str(e)) from e
