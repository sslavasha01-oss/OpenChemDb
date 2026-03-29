import enum

from sqlalchemy import UniqueConstraint, Column, Integer, String, Text, DateTime, ForeignKey, Enum, text
from sqlalchemy.orm import relationship
from app.core.db import Base
from app.models.evaluations import TargetTable
from .enums import ReactionTargetType, ReactionType

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    target_table = Column(
        Enum(TargetTable, name="comment_target", native_enum=True),
        nullable=False
    )
    entry_id = Column(Integer, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_nickname = Column(String, nullable=False)

    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), index=True)
    updated_at = Column(DateTime, server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
                        onupdate=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"))

    # Связь с ответами
    replies = relationship("CommentReply", back_populates="parent_comment", cascade="all, delete-orphan")


class CommentReply(Base):
    __tablename__ = "comment_replies"

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user_nickname = Column(String, nullable=False)

    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), index=True)

    parent_comment = relationship("Comment", back_populates="replies")


class CommentReaction(Base):
    __tablename__ = "comment_reactions"

    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(Enum(ReactionTargetType, name="reaction_target_type", native_enum=True), nullable=False)
    target_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reaction_type = Column(Enum(ReactionType, name="reaction_type", native_enum=True), nullable=False)

    # Уникальность: один юзер — одна реакция на один объект
    __table_args__ = (
        UniqueConstraint('target_type', 'target_id', 'user_id', name='idx_unique_user_reaction'),
    )