from fastapi import APIRouter

from app.deps import CurrentUser
from app.schemas.agent import ToolOut
from app.tools.builtins.registry import list_tools

router = APIRouter()


@router.get("", response_model=list[ToolOut])
async def get_tools(_current_user: CurrentUser) -> list[ToolOut]:
    return list_tools()
