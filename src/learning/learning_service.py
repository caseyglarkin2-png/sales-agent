"""
Learning Service - Sales Training & Coaching
=============================================
Handles courses, lessons, quizzes, and certifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class ContentType(str, Enum):
    """Content type."""
    VIDEO = "video"
    ARTICLE = "article"
    DOCUMENT = "document"
    INTERACTIVE = "interactive"
    QUIZ = "quiz"


class QuestionType(str, Enum):
    """Quiz question type."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    MATCHING = "matching"


class DifficultyLevel(str, Enum):
    """Difficulty level."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class QuizQuestion:
    """A quiz question."""
    id: str
    question: str
    question_type: QuestionType
    options: list[str] = field(default_factory=list)
    correct_answer: str = ""
    correct_answers: list[str] = field(default_factory=list)  # For multiple correct
    explanation: str = ""
    points: int = 1


@dataclass
class Quiz:
    """A quiz."""
    id: str
    title: str
    description: str
    
    # Questions
    questions: list[QuizQuestion] = field(default_factory=list)
    
    # Settings
    passing_score: float = 70.0
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 3
    shuffle_questions: bool = False
    show_answers: bool = True
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Lesson:
    """A lesson in a course."""
    id: str
    title: str
    description: str
    order: int
    
    # Content
    content_type: ContentType = ContentType.VIDEO
    content_url: Optional[str] = None
    content_html: Optional[str] = None
    duration_minutes: int = 0
    
    # Quiz
    quiz_id: Optional[str] = None
    
    # Requirements
    required: bool = True
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Course:
    """A training course."""
    id: str
    title: str
    description: str
    
    # Category
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    
    # Content
    lessons: list[Lesson] = field(default_factory=list)
    thumbnail_url: Optional[str] = None
    
    # Duration
    estimated_hours: float = 0.0
    
    # Requirements
    prerequisites: list[str] = field(default_factory=list)  # Course IDs
    
    # Certification
    certification_id: Optional[str] = None
    
    # Status
    is_published: bool = False
    is_featured: bool = False
    
    # Metrics
    enrollments: int = 0
    completions: int = 0
    avg_rating: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Certification:
    """A certification."""
    id: str
    name: str
    description: str
    
    # Requirements
    required_courses: list[str] = field(default_factory=list)
    passing_score: float = 80.0
    
    # Validity
    valid_months: int = 12
    
    # Badge
    badge_url: Optional[str] = None
    
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LearningPath:
    """A structured learning path."""
    id: str
    name: str
    description: str
    
    # Courses in order
    course_ids: list[str] = field(default_factory=list)
    
    # Target
    role: Optional[str] = None
    level: DifficultyLevel = DifficultyLevel.BEGINNER
    
    # Duration
    estimated_weeks: int = 4
    
    # Certification
    certification_id: Optional[str] = None
    
    is_published: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Enrollment:
    """A user's enrollment in a course."""
    id: str
    user_id: str
    course_id: str
    
    # Progress
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    progress_percent: float = 0.0
    
    # Lessons completed
    completed_lessons: list[str] = field(default_factory=list)
    current_lesson_id: Optional[str] = None
    
    # Quiz results
    quiz_attempts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    
    # Status
    status: str = "active"  # active, completed, abandoned


@dataclass
class QuizAttempt:
    """A quiz attempt."""
    id: str
    user_id: str
    quiz_id: str
    
    # Answers
    answers: dict[str, Any] = field(default_factory=dict)  # question_id -> answer
    
    # Score
    score: float = 0.0
    passed: bool = False
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    time_spent_seconds: int = 0


@dataclass
class UserCertification:
    """A user's earned certification."""
    id: str
    user_id: str
    certification_id: str
    
    # Earned
    earned_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    # Score
    score: float = 0.0


class LearningService:
    """Service for learning management."""
    
    def __init__(self):
        self.courses: dict[str, Course] = {}
        self.quizzes: dict[str, Quiz] = {}
        self.certifications: dict[str, Certification] = {}
        self.learning_paths: dict[str, LearningPath] = {}
        self.enrollments: dict[str, Enrollment] = {}
        self.user_certs: dict[str, list[UserCertification]] = {}
        self._init_sample_data()
    
    def _init_sample_data(self) -> None:
        """Initialize sample courses."""
        # Product knowledge course
        product_quiz = Quiz(
            id="quiz-product",
            title="Product Knowledge Quiz",
            description="Test your product knowledge",
            questions=[
                QuizQuestion(
                    id="q1",
                    question="What is the main value proposition?",
                    question_type=QuestionType.MULTIPLE_CHOICE,
                    options=["Speed", "Cost", "Quality", "All of the above"],
                    correct_answer="All of the above",
                    points=10,
                ),
                QuizQuestion(
                    id="q2",
                    question="True or False: Our product supports API integrations",
                    question_type=QuestionType.TRUE_FALSE,
                    options=["True", "False"],
                    correct_answer="True",
                    points=5,
                ),
            ],
            passing_score=70.0,
        )
        self.quizzes[product_quiz.id] = product_quiz
        
        product_course = Course(
            id="course-product",
            title="Product Fundamentals",
            description="Learn the core product features and value proposition",
            category="product",
            difficulty=DifficultyLevel.BEGINNER,
            lessons=[
                Lesson(
                    id="lesson-1",
                    title="Introduction to Our Product",
                    description="Overview of the product",
                    order=1,
                    content_type=ContentType.VIDEO,
                    duration_minutes=15,
                ),
                Lesson(
                    id="lesson-2",
                    title="Key Features",
                    description="Deep dive into features",
                    order=2,
                    content_type=ContentType.VIDEO,
                    duration_minutes=30,
                    quiz_id="quiz-product",
                ),
            ],
            is_published=True,
            estimated_hours=1.5,
        )
        
        # Sales methodology course
        sales_course = Course(
            id="course-sales",
            title="Sales Methodology",
            description="Our proven sales methodology",
            category="sales",
            difficulty=DifficultyLevel.INTERMEDIATE,
            lessons=[
                Lesson(
                    id="lesson-s1",
                    title="Discovery Process",
                    description="How to conduct effective discovery",
                    order=1,
                    content_type=ContentType.VIDEO,
                    duration_minutes=45,
                ),
                Lesson(
                    id="lesson-s2",
                    title="Handling Objections",
                    description="Common objections and how to address them",
                    order=2,
                    content_type=ContentType.ARTICLE,
                    duration_minutes=20,
                ),
            ],
            is_published=True,
            estimated_hours=2.0,
        )
        
        self.courses[product_course.id] = product_course
        self.courses[sales_course.id] = sales_course
        
        # Certification
        cert = Certification(
            id="cert-sales",
            name="Certified Sales Professional",
            description="Demonstrates mastery of our sales process",
            required_courses=["course-product", "course-sales"],
            valid_months=12,
        )
        self.certifications[cert.id] = cert
        
        # Learning path
        path = LearningPath(
            id="path-onboarding",
            name="New Hire Onboarding",
            description="Complete onboarding for new sales reps",
            course_ids=["course-product", "course-sales"],
            level=DifficultyLevel.BEGINNER,
            estimated_weeks=2,
            certification_id="cert-sales",
            is_published=True,
        )
        self.learning_paths[path.id] = path
    
    # Course CRUD
    async def create_course(
        self,
        title: str,
        description: str,
        category: str = "general",
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        **kwargs
    ) -> Course:
        """Create a course."""
        course = Course(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            category=category,
            difficulty=difficulty,
            **kwargs
        )
        self.courses[course.id] = course
        return course
    
    async def get_course(self, course_id: str) -> Optional[Course]:
        """Get a course by ID."""
        return self.courses.get(course_id)
    
    async def update_course(
        self,
        course_id: str,
        updates: dict[str, Any]
    ) -> Optional[Course]:
        """Update a course."""
        course = self.courses.get(course_id)
        if not course:
            return None
        
        for key, value in updates.items():
            if hasattr(course, key):
                setattr(course, key, value)
        
        course.updated_at = datetime.utcnow()
        return course
    
    async def list_courses(
        self,
        category: Optional[str] = None,
        difficulty: Optional[DifficultyLevel] = None,
        published_only: bool = True,
        limit: int = 100
    ) -> list[Course]:
        """List courses."""
        courses = list(self.courses.values())
        
        if category:
            courses = [c for c in courses if c.category == category]
        if difficulty:
            courses = [c for c in courses if c.difficulty == difficulty]
        if published_only:
            courses = [c for c in courses if c.is_published]
        
        courses.sort(key=lambda c: c.title)
        return courses[:limit]
    
    async def publish_course(self, course_id: str) -> bool:
        """Publish a course."""
        course = self.courses.get(course_id)
        if not course:
            return False
        
        course.is_published = True
        course.updated_at = datetime.utcnow()
        return True
    
    # Lesson management
    async def add_lesson(
        self,
        course_id: str,
        title: str,
        description: str,
        content_type: ContentType,
        order: Optional[int] = None,
        **kwargs
    ) -> Optional[Lesson]:
        """Add a lesson to a course."""
        course = self.courses.get(course_id)
        if not course:
            return None
        
        if order is None:
            order = len(course.lessons) + 1
        
        lesson = Lesson(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            content_type=content_type,
            order=order,
            **kwargs
        )
        
        course.lessons.append(lesson)
        course.lessons.sort(key=lambda l: l.order)
        course.updated_at = datetime.utcnow()
        
        # Update estimated hours
        total_minutes = sum(l.duration_minutes for l in course.lessons)
        course.estimated_hours = total_minutes / 60
        
        return lesson
    
    async def update_lesson(
        self,
        course_id: str,
        lesson_id: str,
        updates: dict[str, Any]
    ) -> Optional[Lesson]:
        """Update a lesson."""
        course = self.courses.get(course_id)
        if not course:
            return None
        
        lesson = next((l for l in course.lessons if l.id == lesson_id), None)
        if not lesson:
            return None
        
        for key, value in updates.items():
            if hasattr(lesson, key):
                setattr(lesson, key, value)
        
        course.updated_at = datetime.utcnow()
        return lesson
    
    # Quiz management
    async def create_quiz(
        self,
        title: str,
        description: str,
        questions: list[dict[str, Any]] = None,
        passing_score: float = 70.0,
        **kwargs
    ) -> Quiz:
        """Create a quiz."""
        quiz_questions = []
        if questions:
            for q in questions:
                quiz_questions.append(QuizQuestion(
                    id=str(uuid.uuid4()),
                    question=q.get("question", ""),
                    question_type=QuestionType(q.get("type", "multiple_choice")),
                    options=q.get("options", []),
                    correct_answer=q.get("correct_answer", ""),
                    points=q.get("points", 1),
                ))
        
        quiz = Quiz(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            questions=quiz_questions,
            passing_score=passing_score,
            **kwargs
        )
        self.quizzes[quiz.id] = quiz
        return quiz
    
    async def get_quiz(self, quiz_id: str) -> Optional[Quiz]:
        """Get a quiz by ID."""
        return self.quizzes.get(quiz_id)
    
    async def submit_quiz(
        self,
        user_id: str,
        quiz_id: str,
        answers: dict[str, Any]
    ) -> Optional[QuizAttempt]:
        """Submit a quiz attempt."""
        quiz = self.quizzes.get(quiz_id)
        if not quiz:
            return None
        
        # Grade the quiz
        total_points = sum(q.points for q in quiz.questions)
        earned_points = 0
        
        for question in quiz.questions:
            user_answer = answers.get(question.id)
            if user_answer == question.correct_answer:
                earned_points += question.points
        
        score = (earned_points / total_points * 100) if total_points > 0 else 0
        passed = score >= quiz.passing_score
        
        attempt = QuizAttempt(
            id=str(uuid.uuid4()),
            user_id=user_id,
            quiz_id=quiz_id,
            answers=answers,
            score=score,
            passed=passed,
            completed_at=datetime.utcnow(),
        )
        
        return attempt
    
    # Enrollment
    async def enroll(
        self,
        user_id: str,
        course_id: str
    ) -> Optional[Enrollment]:
        """Enroll a user in a course."""
        course = self.courses.get(course_id)
        if not course:
            return None
        
        enrollment = Enrollment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            course_id=course_id,
            current_lesson_id=course.lessons[0].id if course.lessons else None,
        )
        
        self.enrollments[enrollment.id] = enrollment
        course.enrollments += 1
        
        return enrollment
    
    async def get_enrollment(self, enrollment_id: str) -> Optional[Enrollment]:
        """Get an enrollment by ID."""
        return self.enrollments.get(enrollment_id)
    
    async def get_user_enrollments(self, user_id: str) -> list[Enrollment]:
        """Get all enrollments for a user."""
        return [e for e in self.enrollments.values() if e.user_id == user_id]
    
    async def complete_lesson(
        self,
        enrollment_id: str,
        lesson_id: str
    ) -> bool:
        """Mark a lesson as complete."""
        enrollment = self.enrollments.get(enrollment_id)
        if not enrollment:
            return False
        
        course = self.courses.get(enrollment.course_id)
        if not course:
            return False
        
        if lesson_id not in enrollment.completed_lessons:
            enrollment.completed_lessons.append(lesson_id)
        
        # Update progress
        total_lessons = len(course.lessons)
        enrollment.progress_percent = (len(enrollment.completed_lessons) / total_lessons * 100) if total_lessons > 0 else 0
        
        # Check for course completion
        if enrollment.progress_percent >= 100:
            enrollment.status = "completed"
            enrollment.completed_at = datetime.utcnow()
            course.completions += 1
        else:
            # Move to next lesson
            current_idx = next((i for i, l in enumerate(course.lessons) if l.id == lesson_id), -1)
            if current_idx >= 0 and current_idx < len(course.lessons) - 1:
                enrollment.current_lesson_id = course.lessons[current_idx + 1].id
        
        return True
    
    # Certifications
    async def create_certification(
        self,
        name: str,
        description: str,
        required_courses: list[str],
        **kwargs
    ) -> Certification:
        """Create a certification."""
        cert = Certification(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            required_courses=required_courses,
            **kwargs
        )
        self.certifications[cert.id] = cert
        return cert
    
    async def get_certification(self, cert_id: str) -> Optional[Certification]:
        """Get a certification by ID."""
        return self.certifications.get(cert_id)
    
    async def check_certification_eligibility(
        self,
        user_id: str,
        certification_id: str
    ) -> dict[str, Any]:
        """Check if user is eligible for a certification."""
        cert = self.certifications.get(certification_id)
        if not cert:
            return {"eligible": False, "reason": "Certification not found"}
        
        user_enrollments = await self.get_user_enrollments(user_id)
        completed_courses = [e.course_id for e in user_enrollments if e.status == "completed"]
        
        missing = [c for c in cert.required_courses if c not in completed_courses]
        
        return {
            "eligible": len(missing) == 0,
            "completed_courses": completed_courses,
            "missing_courses": missing,
            "progress": len([c for c in cert.required_courses if c in completed_courses]) / len(cert.required_courses) * 100 if cert.required_courses else 100,
        }
    
    async def award_certification(
        self,
        user_id: str,
        certification_id: str,
        score: float = 100.0
    ) -> Optional[UserCertification]:
        """Award a certification to a user."""
        cert = self.certifications.get(certification_id)
        if not cert:
            return None
        
        from datetime import timedelta
        
        user_cert = UserCertification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            certification_id=certification_id,
            score=score,
            expires_at=datetime.utcnow() + timedelta(days=cert.valid_months * 30) if cert.valid_months else None,
        )
        
        if user_id not in self.user_certs:
            self.user_certs[user_id] = []
        
        self.user_certs[user_id].append(user_cert)
        return user_cert
    
    async def get_user_certifications(self, user_id: str) -> list[UserCertification]:
        """Get all certifications for a user."""
        return self.user_certs.get(user_id, [])
    
    # Learning paths
    async def create_learning_path(
        self,
        name: str,
        description: str,
        course_ids: list[str],
        **kwargs
    ) -> LearningPath:
        """Create a learning path."""
        path = LearningPath(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            course_ids=course_ids,
            **kwargs
        )
        self.learning_paths[path.id] = path
        return path
    
    async def get_learning_path(self, path_id: str) -> Optional[LearningPath]:
        """Get a learning path by ID."""
        return self.learning_paths.get(path_id)
    
    async def list_learning_paths(
        self,
        role: Optional[str] = None,
        published_only: bool = True
    ) -> list[LearningPath]:
        """List learning paths."""
        paths = list(self.learning_paths.values())
        
        if role:
            paths = [p for p in paths if p.role == role]
        if published_only:
            paths = [p for p in paths if p.is_published]
        
        paths.sort(key=lambda p: p.name)
        return paths
    
    async def get_path_progress(
        self,
        user_id: str,
        path_id: str
    ) -> dict[str, Any]:
        """Get user's progress on a learning path."""
        path = self.learning_paths.get(path_id)
        if not path:
            return {}
        
        user_enrollments = await self.get_user_enrollments(user_id)
        enrollment_map = {e.course_id: e for e in user_enrollments}
        
        course_progress = []
        for course_id in path.course_ids:
            enrollment = enrollment_map.get(course_id)
            course = self.courses.get(course_id)
            
            course_progress.append({
                "course_id": course_id,
                "course_title": course.title if course else "Unknown",
                "enrolled": enrollment is not None,
                "status": enrollment.status if enrollment else "not_started",
                "progress": enrollment.progress_percent if enrollment else 0,
            })
        
        total_progress = sum(c["progress"] for c in course_progress) / len(course_progress) if course_progress else 0
        
        return {
            "path_id": path_id,
            "courses": course_progress,
            "total_progress": total_progress,
            "completed": total_progress >= 100,
        }


# Singleton instance
_learning_service: Optional[LearningService] = None


def get_learning_service() -> LearningService:
    """Get learning service singleton."""
    global _learning_service
    if _learning_service is None:
        _learning_service = LearningService()
    return _learning_service
