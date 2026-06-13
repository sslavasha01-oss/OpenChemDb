from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Dict

from app.api.deps import get_current_user
from app.core.db import get_archive_db
from app.models.evaluations import EntryEvaluation, EvaluationStatus, TargetTable

from app.models.user import User

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post("/add")
async def add_evaluation(
    target: TargetTable,
    entry_id: int,
    status: EvaluationStatus,
    comment: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_archive_db)
):
    """
    Добавляет или обновляет реакцию.
    Доступно только авторизованным пользователям.
    """
    nickname = current_user.username # Используем ник из токена
    """
    Добавляет или обновляет реакцию пользователя на запись.
    """
    # Проверяем, существует ли уже оценка (Upsert логика)
    query = select(EntryEvaluation).where(
        EntryEvaluation.user_id == current_user.id,
        EntryEvaluation.target_table == target,
        EntryEvaluation.entry_id == entry_id
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        existing.status = status
        existing.comment = comment
        existing.user_nickname = nickname
    else:
        new_eval = EntryEvaluation(
            user_id=current_user.id,
            user_nickname=nickname,
            target_table=target,
            entry_id=entry_id,
            status=status,
            comment=comment
        )
        db.add(new_eval)

    try:
        await db.commit()
    except Exception:

       await db.rollback()
       raise HTTPException(status_code=400, detail="Ошибка при сохранении оценки")

    return {"status": "ok"}


@router.get("/batch")
async def get_evaluations_batch(
        target: TargetTable,
        entry_ids: List[int] = Query(...),
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Эффективно получает все оценки для списка ID одним запросом.
    Возвращает словарь: {entry_id: [список статусов]}
    """
    if not entry_ids:
        return {}

    query = select(EntryEvaluation).where(
        EntryEvaluation.target_table == target,
        EntryEvaluation.entry_id.in_(entry_ids)
    )

    result = await db.execute(query)
    evals = result.scalars().all()

    # Группируем результаты для фронтенда
    # Чтобы фронт сразу видел: "У этой реакции 5 CHECK и 1 ERROR"
    report = {eid: {"CHECK": 0, "POO": 0, "ERROR": 0} for eid in entry_ids}

    for e in evals:
        if e.entry_id in report:
            report[e.entry_id][e.status.value] += 1

    return report


@router.get("/recent-problems")
async def get_recent_problems(
        limit: int = 50,
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Возвращает последние записи со статусом POO или ERROR.
    """
    query = (
        select(EntryEvaluation)
        .where(EntryEvaluation.status.in_([EvaluationStatus.POO, EvaluationStatus.ERROR]))
        .order_by(EntryEvaluation.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    problems = result.scalars().all()

    return problems


@router.get("/details")
async def get_evaluation_details(
    target: TargetTable,
    entry_id: int,
    status: EvaluationStatus = None,
    db: AsyncSession = Depends(get_archive_db)
):
    """
    Возвращает список всех пользователей и их комментариев для конкретной записи.
    Используется для тултипов при наведении на иконку статуса.
    """
    query = select(
        EntryEvaluation.user_id,
        EntryEvaluation.user_nickname,
        EntryEvaluation.status,
        EntryEvaluation.comment,
        EntryEvaluation.created_at
    ).where(
        EntryEvaluation.target_table == target,
        EntryEvaluation.entry_id == entry_id
    )

    # Если передали статус (например, только POO), фильтруем по нему
    if status:
        query = query.where(EntryEvaluation.status == status)

    # Сортируем: сначала свежие отзывы
    query = query.order_by(EntryEvaluation.created_at.desc())

    result = await db.execute(query)
    evals = result.all()

    # Формируем красивый список объектов
    return [
        {
            "user_id": row.user_id,
            "user": row.user_nickname,
            "status": row.status,
            "comment": row.comment,
            "date": row.created_at.strftime("%Y-%m-%d %H:%M") if row.created_at else None
        }
        for row in evals
    ]


@router.patch("/update-comment")
async def update_evaluation_comment(
        target: TargetTable,
        entry_id: int,
        comment: str = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Изменяет только комментарий у существующей оценки текущего пользователя.
    """
    query = select(EntryEvaluation).where(
        EntryEvaluation.user_id == current_user.id,
        EntryEvaluation.target_table == target,
        EntryEvaluation.entry_id == entry_id
    )
    result = await db.execute(query)
    evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оценка не найдена или у вас нет прав на её изменение"
        )

    evaluation.comment = comment

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при обновлении комментария")

    return {"status": "updated", "comment": comment}


@router.delete("/delete")
async def delete_evaluation(
        target: TargetTable,
        entry_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Удаляет оценку текущего пользователя для указанной записи.
    """
    stmt = delete(EntryEvaluation).where(
        EntryEvaluation.user_id == current_user.id,
        EntryEvaluation.target_table == target,
        EntryEvaluation.entry_id == entry_id
    ).returning(EntryEvaluation.id)  # Возвращает ID удаленной строки, если она была

    result = await db.execute(stmt)
    deleted_id = result.scalar_one_or_none()

    if not deleted_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Оценка не найдена или уже удалена"
        )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Ошибка при удалении оценки")

    return {"status": "deleted"}