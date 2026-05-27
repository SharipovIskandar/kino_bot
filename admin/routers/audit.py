import math

from fastapi import APIRouter, Request
from sqlalchemy import select, func, desc

from admin.responses import render
from bot.database.connection import AsyncSessionFactory
from bot.database.models import AdminAction

router = APIRouter()
PER_PAGE = 30


@router.get("")
async def audit_log(request: Request, page: int = 1, action: str = "", admin_id: str = ""):
    offset = (page - 1) * PER_PAGE
    async with AsyncSessionFactory() as session:
        base = select(AdminAction)
        if action:
            base = base.where(AdminAction.action_type == action)
        if admin_id:
            try:
                base = base.where(AdminAction.admin_telegram_id == int(admin_id))
            except ValueError:
                pass

        total_r = await session.execute(select(func.count()).select_from(base.subquery()))
        total = total_r.scalar_one()

        actions_r = await session.execute(
            base.order_by(desc(AdminAction.created_at)).limit(PER_PAGE).offset(offset)
        )
        actions = list(actions_r.scalars().all())

        # Mavjud action turlari (filter dropdown uchun)
        types_r = await session.execute(
            select(AdminAction.action_type).distinct().order_by(AdminAction.action_type)
        )
        action_types = [row[0] for row in types_r.all()]

    return render(
        request, "audit/index.html",
        actions=actions, total=total, page=page,
        total_pages=math.ceil(total / PER_PAGE) if total else 1,
        action_types=action_types,
        current_action=action,
        current_admin=admin_id,
    )
