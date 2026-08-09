"""§16.12 — mounted at the same `/api/v1/workflows` prefix as
app.api.v1.workflows, and included BEFORE it in main.py: `/generate` and
`/{workflow_id}` are both single path segments, so if the parameterized
workflows router matched first, a request for `/workflows/generate` would
be captured as `workflow_id="generate"` instead of reaching this router."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.database.models import WorkflowGenerationRequest
from app.deps import CurrentOrg, CurrentUser, DbSession
from app.schemas.workflow import WorkflowOut
from app.schemas.workflow_generation import (
    AnswerRequest,
    CompileError,
    GenerateCreateRequest,
    RejectRequest,
    WorkflowGenerationRequestOut,
)
from app.services import workflow_generation_service
from app.worker.tasks import generate_workflow_plan_task
from app.workflows.graph import GraphValidationError

router = APIRouter()


def _request_out(request: WorkflowGenerationRequest) -> WorkflowGenerationRequestOut:
    return WorkflowGenerationRequestOut.model_validate(request, from_attributes=True)


async def _get_request_or_404(
    db: DbSession, ctx: CurrentOrg, request_id: uuid.UUID
) -> WorkflowGenerationRequest:
    request = await workflow_generation_service.get_request(
        db, org_id=ctx.org.id, request_id=request_id
    )
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Generation request not found.")
    return request


@router.post(
    "/generate", response_model=WorkflowGenerationRequestOut, status_code=status.HTTP_202_ACCEPTED
)
async def generate_workflow(
    body: GenerateCreateRequest, ctx: CurrentOrg, user: CurrentUser, db: DbSession
) -> WorkflowGenerationRequestOut:
    request = await workflow_generation_service.create_request(
        db, org_id=ctx.org.id, user_id=user.id, description=body.description
    )
    # Commit before enqueueing — same reasoning as POST /workflows/{id}/run:
    # the worker is a separate connection and won't see this row otherwise.
    await db.commit()
    generate_workflow_plan_task.delay(str(request.id))
    return _request_out(request)


@router.get("/generate/{request_id}", response_model=WorkflowGenerationRequestOut)
async def get_generation_request(
    request_id: uuid.UUID, ctx: CurrentOrg, db: DbSession
) -> WorkflowGenerationRequestOut:
    request = await _get_request_or_404(db, ctx, request_id)
    return _request_out(request)


@router.post("/generate/{request_id}/answer", response_model=WorkflowGenerationRequestOut)
async def answer_clarifying_question(
    request_id: uuid.UUID, body: AnswerRequest, ctx: CurrentOrg, db: DbSession
) -> WorkflowGenerationRequestOut:
    request = await _get_request_or_404(db, ctx, request_id)
    if request.status != "awaiting_answers":
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Request isn't awaiting an answer (status={request.status})."
        )
    all_answered = await workflow_generation_service.submit_answer(
        db, request=request, answer=body.answer
    )
    await db.commit()
    if all_answered:
        generate_workflow_plan_task.delay(str(request.id))
    return _request_out(request)


@router.post("/generate/{request_id}/compile")
async def compile_generation_request(
    request_id: uuid.UUID, ctx: CurrentOrg, db: DbSession
) -> WorkflowOut | WorkflowGenerationRequestOut:
    request = await _get_request_or_404(db, ctx, request_id)

    if request.status in ("applied", "rejected"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request already {request.status}.")

    if not request.plan:
        # No plan to compile yet (still pending/planning/awaiting_answers
        # with nothing to show) — "explicit generate now": force a final
        # round even if some questions are still unanswered, rather than
        # waiting further.
        await db.commit()
        generate_workflow_plan_task.delay(str(request.id), True)
        return _request_out(request)

    # A plan already exists — ready, or previously failed to *compile*
    # (e.g. it referenced an agent that didn't exist yet). Retry compiling
    # this same plan directly rather than re-running the planner: the
    # common next action here is "I just created the missing agent."
    try:
        workflow = await workflow_generation_service.compile_and_save(
            db, request=request, workflow_name=_derive_workflow_name(request)
        )
    except (CompileError, GraphValidationError) as exc:
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "; ".join(exc.errors)) from exc

    await db.commit()
    return WorkflowOut.model_validate(workflow, from_attributes=True)


def _derive_workflow_name(request: WorkflowGenerationRequest) -> str:
    text = request.raw_text.strip()
    return text[:97] + "..." if len(text) > 100 else text


@router.post("/edit-with-nl/{request_id}/apply", response_model=WorkflowOut)
async def apply_nl_edit(request_id: uuid.UUID, ctx: CurrentOrg, db: DbSession) -> WorkflowOut:
    request = await _get_request_or_404(db, ctx, request_id)
    try:
        workflow = await workflow_generation_service.apply_edit(db, request=request)
    except (CompileError, GraphValidationError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "; ".join(exc.errors)) from exc
    await db.commit()
    return WorkflowOut.model_validate(workflow, from_attributes=True)


@router.post("/edit-with-nl/{request_id}/reject", response_model=WorkflowGenerationRequestOut)
async def reject_nl_edit(
    request_id: uuid.UUID, body: RejectRequest, ctx: CurrentOrg, db: DbSession
) -> WorkflowGenerationRequestOut:
    request = await _get_request_or_404(db, ctx, request_id)
    await workflow_generation_service.reject_request(db, request=request, reason=body.reason)
    await db.commit()
    return _request_out(request)
