from app.models.academic import Course, GraduationRequirement, Major, PracticeCourse, StudentCourse
from app.models.academic_warning import AcademicWarning
from app.models.ai import AIConversation, AIMessage
from app.models.error_case import ErrorCase
from app.models.forum import ForumComment, ForumFile, ForumTopic, ForumTopicLike
from app.models.knowledge_card import KnowledgeCard
from app.models.openclaw import OpenClawToolAudit
from app.models.schedule import Schedule
from app.models.time_plan import TimePlanEvent
from app.models.user import User

__all__ = [
    "AcademicWarning",
    "AIConversation",
    "AIMessage",
    "Course",
    "ErrorCase",
    "ForumComment",
    "ForumFile",
    "ForumTopic",
    "ForumTopicLike",
    "GraduationRequirement",
    "KnowledgeCard",
    "Major",
    "OpenClawToolAudit",
    "PracticeCourse",
    "Schedule",
    "StudentCourse",
    "TimePlanEvent",
    "User",
]
