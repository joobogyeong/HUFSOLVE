from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Problem, SampleRun
from ..queue.factory import get_queue_client
from ..schemas import SampleRunCreate, SampleRunCreated, SampleRunRead

router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=SampleRunCreated, status_code=202)
def create_sample_run(
    request: SampleRunCreate,
    db: Session = Depends(get_db),
) -> SampleRunCreated:
    problem = db.get(Problem, request.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    if request.sample_index >= len(problem.samples):
        raise HTTPException(status_code=400, detail="Sample index out of range")

    sample = problem.samples[request.sample_index]
    sample_run = SampleRun(
        problem_id=problem.id,
        language=request.language,
        source_code=request.source_code,
        sample_index=request.sample_index,
        input_data=sample["input"],
        expected_output=sample["output"],
        status="PENDING",
    )
    db.add(sample_run)
    db.commit()
    db.refresh(sample_run)

    try:
        get_queue_client().enqueue_sample_run(sample_run.id)
    except Exception as exc:
        sample_run.status = "SYSTEM_ERROR"
        sample_run.stderr = f"Failed to enqueue sample run: {exc}"
        db.commit()
        raise HTTPException(status_code=502, detail="Failed to enqueue sample run") from exc

    return SampleRunCreated(run_id=sample_run.id, status=sample_run.status)


@router.get("/runs/{run_id}", response_model=SampleRunRead)
def get_sample_run(run_id: int, db: Session = Depends(get_db)) -> SampleRunRead:
    sample_run = db.get(SampleRun, run_id)
    if sample_run is None:
        raise HTTPException(status_code=404, detail="Sample run not found")

    return SampleRunRead.from_model(sample_run)
