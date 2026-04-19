from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_users_db
from app.models.comments import Comment, CommentReply
from app.models.evaluations import TargetTable
from app.models.user import User

router = APIRouter(prefix="/comments", tags=["Comments"])


@router.post("/add")
async def add_comment(
        target: TargetTable,
        entry_id: int,
        content: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    new_comment = Comment(
        target_table=target,
        entry_id=entry_id,
        user_id=current_user.id,
        user_nickname=current_user.username,
        content=content
    )
    db.add(new_comment)
    await db.commit()
    return {"status": "success", "comment_id": new_comment.id}


@router.post("/reply/add")
async def add_reply(
        comment_id: int,
        content: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    # Проверяем, существует ли родительский комментарий
    parent = await db.get(Comment, comment_id)
    if not parent:
        raise HTTPException(status_code=404, detail="Comment not found")

    new_reply = CommentReply(
        comment_id=comment_id,
        user_id=current_user.id,
        user_nickname=current_user.username,
        content=content
    )
    db.add(new_reply)
    await db.commit()
    return {"status": "success", "reply_id": new_reply.id}


@router.get("/list")
async def get_comments(
        target: TargetTable,
        entry_id: int,
        limit: int = Query(10, ge=1, le=100),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_users_db)
):
    """Выдает список основных комментариев для записи"""
    query = (
        select(Comment)
        .where(Comment.target_table == target, Comment.entry_id == entry_id)
        .order_by(Comment.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    comments = result.scalars().all()
    #
    # Считаем общее кол-во для пагинации на фронте
    count_query = select(func.count()).select_from(Comment).where(Comment.target_table == target,
                                                                  Comment.entry_id == entry_id)
    total = (await db.execute(count_query)).scalar()
    return {
        "total": total,
        "items": comments
    }


@router.get("/batch-counts")
async def get_comments_batch_counts(
        target: TargetTable,
        entry_ids: List[int] = Query(...),
        db: AsyncSession = Depends(get_users_db)
) -> Dict[int, int]:
    """
    Возвращает словарь {entry_id: count} для списка переданных ID записей.
    """
    if not entry_ids:
        return {}

    # Формируем запрос с группировкой
    query = (
        select(Comment.entry_id, func.count(Comment.id))
        .where(
            Comment.target_table == target,
            Comment.entry_id.in_(entry_ids)
        )
        .group_by(Comment.entry_id)
    )

    result = await db.execute(query)
    # Превращаем результат выполнения в удобный dict {id: count}
    counts_map = {row[0]: row[1] for row in result.all()}

    # Дозаполняем нулями те ID, для которых комментариев не нашлось
    return {eid: counts_map.get(eid, 0) for eid in entry_ids}


@router.get("/replies/{comment_id}")
async def get_replies(
        comment_id: int,
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
        db: AsyncSession = Depends(get_users_db)
):
    """Выдает ответы на конкретный комментарий"""
    query = (
        select(CommentReply)
        .where(CommentReply.comment_id == comment_id)
        .order_by(CommentReply.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/replies-batch-count")
async def get_replies_count(
        comment_ids: List[int] = Query(...),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Принимает список comment_id, возвращает словарь вида:
    {"comment_id": count, ...}
    """
    # Запрос: считаем количество строк в CommentReply, где comment_id есть в списке
    query = (
        select(CommentReply.comment_id, func.count(CommentReply.id))
        .where(CommentReply.comment_id.in_(comment_ids))
        .group_by(CommentReply.comment_id)
    )

    result = await db.execute(query)
    # Преобразуем результат в словарь
    counts = {row[0]: row[1] for row in result.all()}

    # Чтобы фронту было удобнее, можно вернуть количество для всех ID,
    # даже если ответов 0 (т.е. ID не нашелся в базе)
    return {cid: counts.get(cid, 0) for cid in comment_ids}
