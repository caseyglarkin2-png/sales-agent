"""
Learning Routes - Learning API Endpoints
=========================================
RESTful API for sales training and learning management.
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.learning import LearningService, get_learning_service


router = APIRouter(prefix="/learning", tags=["Learning"])


# Request/Response Models
class CreateCourseRequest(BaseModel):
    title: str
    description: str
    category: str = "general"
    difficulty: str = "beginner"
    tags: list[str] = []
    estimated_hours: float = 0.0
    prerequisites: list[str] = []


class UpdateCourseRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    is_featured: Optional[bool] = None


class AddLessonRequest(BaseModel):
    title: str
    description: str
    content_type: str
    order: Optional[int] = None
    content_url: Optional[str] = None
    content_html: Optional[str] = None
    duration_minutes: int = 0
    quiz_id: Optional[str] = None
    required: bool = True


class UpdateLessonRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content_url: Optional[str] = None
    duration_minutes: Optional[int] = None


class CreateQuizRequest(BaseModel):
    title: str
    description: str
    questions: list[dict[str, Any]] = []
    passing_score: float = 70.0
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 3


class SubmitQuizRequest(BaseModel):
    user_id: str
    answers: dict[str, Any]


class EnrollRequest(BaseModel):
    user_id: str
    course_id: str


class CompleteLessonRequest(BaseModel):
    lesson_id: str


class CreateCertificationRequest(BaseModel):
    name: str
    description: str
    required_courses: list[str]
    passing_score: float = 80.0
    valid_months: int = 12


class CreateLearningPathRequest(BaseModel):
    name: str
    description: str
    course_ids: list[str]
    role: Optional[str] = None
    level: str = "beginner"
    estimated_weeks: int = 4


# Helper
def get_service() -> LearningService:
    return get_learning_service()


# Course endpoints
@router.post("/courses")
async def create_course(request: CreateCourseRequest):
    """Create a course."""
    service = get_service()
    from src.learning.learning_service import DifficultyLevel
    
    course = await service.create_course(
        title=request.title,
        description=request.description,
        category=request.category,
        difficulty=DifficultyLevel(request.difficulty),
        tags=request.tags,
        estimated_hours=request.estimated_hours,
        prerequisites=request.prerequisites,
    )
    
    return {"course": course}


@router.get("/courses")
async def list_courses(
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    published_only: bool = Query(True),
    limit: int = Query(100, le=500)
):
    """List courses."""
    service = get_service()
    from src.learning.learning_service import DifficultyLevel
    
    diff_enum = DifficultyLevel(difficulty) if difficulty else None
    courses = await service.list_courses(
        category=category,
        difficulty=diff_enum,
        published_only=published_only,
        limit=limit,
    )
    
    return {"courses": courses, "count": len(courses)}


@router.get("/courses/{course_id}")
async def get_course(course_id: str):
    """Get a course."""
    service = get_service()
    course = await service.get_course(course_id)
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"course": course}


@router.put("/courses/{course_id}")
async def update_course(course_id: str, request: UpdateCourseRequest):
    """Update a course."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    course = await service.update_course(course_id, updates)
    
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"course": course}


@router.post("/courses/{course_id}/publish")
async def publish_course(course_id: str):
    """Publish a course."""
    service = get_service()
    success = await service.publish_course(course_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot publish course")
    
    course = await service.get_course(course_id)
    return {"course": course}


# Lesson endpoints
@router.post("/courses/{course_id}/lessons")
async def add_lesson(course_id: str, request: AddLessonRequest):
    """Add a lesson to a course."""
    service = get_service()
    from src.learning.learning_service import ContentType
    
    lesson = await service.add_lesson(
        course_id=course_id,
        title=request.title,
        description=request.description,
        content_type=ContentType(request.content_type),
        order=request.order,
        content_url=request.content_url,
        content_html=request.content_html,
        duration_minutes=request.duration_minutes,
        quiz_id=request.quiz_id,
        required=request.required,
    )
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return {"lesson": lesson}


@router.put("/courses/{course_id}/lessons/{lesson_id}")
async def update_lesson(course_id: str, lesson_id: str, request: UpdateLessonRequest):
    """Update a lesson."""
    service = get_service()
    
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    lesson = await service.update_lesson(course_id, lesson_id, updates)
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Course or lesson not found")
    
    return {"lesson": lesson}


# Quiz endpoints
@router.post("/quizzes")
async def create_quiz(request: CreateQuizRequest):
    """Create a quiz."""
    service = get_service()
    quiz = await service.create_quiz(
        title=request.title,
        description=request.description,
        questions=request.questions,
        passing_score=request.passing_score,
        time_limit_minutes=request.time_limit_minutes,
        max_attempts=request.max_attempts,
    )
    
    return {"quiz": quiz}


@router.get("/quizzes/{quiz_id}")
async def get_quiz(quiz_id: str):
    """Get a quiz."""
    service = get_service()
    quiz = await service.get_quiz(quiz_id)
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return {"quiz": quiz}


@router.post("/quizzes/{quiz_id}/submit")
async def submit_quiz(quiz_id: str, request: SubmitQuizRequest):
    """Submit a quiz attempt."""
    service = get_service()
    attempt = await service.submit_quiz(
        user_id=request.user_id,
        quiz_id=quiz_id,
        answers=request.answers,
    )
    
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    return {"attempt": attempt}


# Enrollment endpoints
@router.post("/enrollments")
async def enroll(request: EnrollRequest):
    """Enroll a user in a course."""
    service = get_service()
    enrollment = await service.enroll(
        user_id=request.user_id,
        course_id=request.course_id,
    )
    
    if not enrollment:
        raise HTTPException(status_code=400, detail="Cannot enroll")
    
    return {"enrollment": enrollment}


@router.get("/enrollments/{enrollment_id}")
async def get_enrollment(enrollment_id: str):
    """Get an enrollment."""
    service = get_service()
    enrollment = await service.get_enrollment(enrollment_id)
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {"enrollment": enrollment}


@router.get("/users/{user_id}/enrollments")
async def get_user_enrollments(user_id: str):
    """Get all enrollments for a user."""
    service = get_service()
    enrollments = await service.get_user_enrollments(user_id)
    
    return {"enrollments": enrollments, "count": len(enrollments)}


@router.post("/enrollments/{enrollment_id}/complete-lesson")
async def complete_lesson(enrollment_id: str, request: CompleteLessonRequest):
    """Mark a lesson as complete."""
    service = get_service()
    success = await service.complete_lesson(
        enrollment_id=enrollment_id,
        lesson_id=request.lesson_id,
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot complete lesson")
    
    enrollment = await service.get_enrollment(enrollment_id)
    return {"enrollment": enrollment}


# Certification endpoints
@router.post("/certifications")
async def create_certification(request: CreateCertificationRequest):
    """Create a certification."""
    service = get_service()
    cert = await service.create_certification(
        name=request.name,
        description=request.description,
        required_courses=request.required_courses,
        passing_score=request.passing_score,
        valid_months=request.valid_months,
    )
    
    return {"certification": cert}


@router.get("/certifications/{cert_id}")
async def get_certification(cert_id: str):
    """Get a certification."""
    service = get_service()
    cert = await service.get_certification(cert_id)
    
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    
    return {"certification": cert}


@router.get("/certifications/{cert_id}/eligibility/{user_id}")
async def check_eligibility(cert_id: str, user_id: str):
    """Check if a user is eligible for a certification."""
    service = get_service()
    result = await service.check_certification_eligibility(user_id, cert_id)
    
    return result


@router.post("/certifications/{cert_id}/award/{user_id}")
async def award_certification(
    cert_id: str,
    user_id: str,
    score: float = Query(100.0)
):
    """Award a certification to a user."""
    service = get_service()
    user_cert = await service.award_certification(
        user_id=user_id,
        certification_id=cert_id,
        score=score,
    )
    
    if not user_cert:
        raise HTTPException(status_code=400, detail="Cannot award certification")
    
    return {"user_certification": user_cert}


@router.get("/users/{user_id}/certifications")
async def get_user_certifications(user_id: str):
    """Get all certifications for a user."""
    service = get_service()
    certs = await service.get_user_certifications(user_id)
    
    return {"certifications": certs, "count": len(certs)}


# Learning path endpoints
@router.post("/paths")
async def create_learning_path(request: CreateLearningPathRequest):
    """Create a learning path."""
    service = get_service()
    from src.learning.learning_service import DifficultyLevel
    
    path = await service.create_learning_path(
        name=request.name,
        description=request.description,
        course_ids=request.course_ids,
        role=request.role,
        level=DifficultyLevel(request.level),
        estimated_weeks=request.estimated_weeks,
    )
    
    return {"learning_path": path}


@router.get("/paths")
async def list_learning_paths(
    role: Optional[str] = Query(None),
    published_only: bool = Query(True)
):
    """List learning paths."""
    service = get_service()
    paths = await service.list_learning_paths(
        role=role,
        published_only=published_only,
    )
    
    return {"learning_paths": paths, "count": len(paths)}


@router.get("/paths/{path_id}")
async def get_learning_path(path_id: str):
    """Get a learning path."""
    service = get_service()
    path = await service.get_learning_path(path_id)
    
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    return {"learning_path": path}


@router.get("/paths/{path_id}/progress/{user_id}")
async def get_path_progress(path_id: str, user_id: str):
    """Get user's progress on a learning path."""
    service = get_service()
    progress = await service.get_path_progress(user_id, path_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Learning path not found")
    
    return progress
