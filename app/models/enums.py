import enum

class ReactionTargetType(str, enum.Enum):
    COMMENT = "COMMENT"
    REPLY = "REPLY"

class ReactionType(str, enum.Enum):
    USEFUL = "USEFUL"
    NOT_USEFUL = "NOT_USEFUL"