from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comments import CommentReaction
from app.models.enums import ReactionTargetType, ReactionType
from app.api.deps import get_current_user
from app.models.user import User
from app.core.db import get_users_db

router = APIRouter(prefix="/comment_reaction", tags=["comment_reaction"])


@router.post("/add")
async def add_reaction(
        target_type: ReactionTargetType,
        target_id: int,
        reaction: ReactionType,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    # Логика: если реакция уже есть — обновляем, если нет — создаем (upsert)
    # Для простоты пока добавим создание. При желании можно сделать update.
    new_reaction = CommentReaction(
        target_type=target_type,
        target_id=target_id,
        user_id=current_user.id,
        reaction_type=reaction
    )
    db.add(new_reaction)
    await db.commit()
    return {"status": "success"}


@router.post("/count")
async def get_reactions_count(
        target_type: ReactionTargetType,
        target_ids: List[int],
        db: AsyncSession = Depends(get_users_db)
):
    """
    Возвращает словарь: {target_id: {"USEFUL": count, "NOT_USEFUL": count}}
    """
    query = (
        select(
            CommentReaction.target_id,
            CommentReaction.reaction_type,
            func.count(CommentReaction.id)
        )
        .where(
            and_(
                CommentReaction.target_type == target_type,
                CommentReaction.target_id.in_(target_ids)
            )
        )
        .group_by(CommentReaction.target_id, CommentReaction.reaction_type)
    )

    result = await db.execute(query)

    # Инициализируем структуру ответов
    counts = {tid: {"USEFUL": 0, "NOT_USEFUL": 0} for tid in target_ids}

    for tid, r_type, count in result.all():
        if tid in counts:
            counts[tid][r_type.value] = count

    return counts