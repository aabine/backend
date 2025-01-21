import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"

class AuthProvider(str, enum.Enum):
    LOCAL = "local"
    GOOGLE = "google"
    MICROSOFT = "microsoft"

class AssessmentType(str, enum.Enum):
    QUIZ = "quiz"
    EXAM = "exam"
    ASSIGNMENT = "assignment"

class QuestionType(str, enum.Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILE_UPLOAD = "file_upload"

class AuditActionType(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ROLE_CHANGE = "role_change"
    PERMISSION_CHANGE = "permission_change"
    SETTINGS_CHANGE = "settings_change"

class NotificationType(str, enum.Enum):
    MESSAGE = "message"
    FORUM = "forum"
    CLASSROOM = "classroom"
    SYSTEM = "system"

class SchoolSubscriptionType(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise" 