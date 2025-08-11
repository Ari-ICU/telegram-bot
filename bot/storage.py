import json
import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Ensure data directory exists
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

EXAM_DB_PATH = os.path.join(DATA_DIR, "exam_data.json")
USER_SESSIONS_PATH = os.path.join(DATA_DIR, "user_sessions.json")
EXAM_RESULTS_PATH = os.path.join(DATA_DIR, "exam_results.json")
LESSON_DB_PATH = os.path.join(DATA_DIR, "lesson.json") 


def load_exam_database() -> Dict[str, Dict]:
    """Load exam database in the original nested grade -> subjects structure."""
    try:
        if not os.path.exists(EXAM_DB_PATH):
            with open(EXAM_DB_PATH, 'w') as f:
                json.dump({}, f)
            logger.info("Created empty exam database at %s", EXAM_DB_PATH)
            return {}
        with open(EXAM_DB_PATH, 'r') as f:
            data = json.load(f)
        for grade_id, grade_data in list(data.items()):
            if 'subjects' not in grade_data:
                logger.warning("Grade %s missing 'subjects' key, removing", grade_id)
                data.pop(grade_id)
                continue
            for subject_id, subject_data in list(grade_data['subjects'].items()):
                required_fields = ['title', 'description', 'duration', 'questions']
                if not all(k in subject_data for k in required_fields):
                    logger.warning("Subject %s in grade %s missing required fields, removing", subject_id, grade_id)
                    grade_data['subjects'].pop(subject_id)
                    continue
        return data
    except Exception as e:
        logger.error("Error loading exam database: %s", e)
        return {}
    
def load_user_sessions() -> Dict[int, Dict]:
    """Load user sessions from JSON file."""
    try:
        if not os.path.exists(USER_SESSIONS_PATH):
            with open(USER_SESSIONS_PATH, 'w') as f:
                json.dump({}, f)
        with open(USER_SESSIONS_PATH, 'r') as f:
            return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        logger.error("Error loading user sessions: %s", e)
        return {}

def save_user_sessions(sessions: Dict[int, Dict]):
    """Save user sessions to JSON file."""
    try:
        with open(USER_SESSIONS_PATH, 'w') as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        logger.error("Error saving user sessions: %s", e)

def load_exam_results() -> Dict[int, List]:
    """Load exam results from JSON file."""
    try:
        if not os.path.exists(EXAM_RESULTS_PATH):
            with open(EXAM_RESULTS_PATH, 'w') as f:
                json.dump({}, f)
        with open(EXAM_RESULTS_PATH, 'r') as f:
            return {int(k): v for k, v in json.load(f).items()}
    except Exception as e:
        logger.error("Error loading exam results: %s", e)
        return {}

def save_exam_results(results: Dict[int, List]):
    """Save exam results to JSON file."""
    try:
        with open(EXAM_RESULTS_PATH, 'w') as f:
            json.dump(results, f, indent=2)
    except Exception as e:
        logger.error("Error saving exam results: %s", e)

def get_user_session(user_id: int) -> Dict:
    """Get or create user session."""
    sessions = load_user_sessions()
    if user_id not in sessions:
        sessions[user_id] = {
            "current_exam": None,
            "current_question": 0,
            "answers": [],
            "start_time": None,
            "exam_active": False
        }
        save_user_sessions(sessions)
    return sessions[user_id]

def update_user_session(user_id: int, session_data: Dict):
    """Update and save user session data."""
    sessions = load_user_sessions()
    sessions[user_id] = session_data
    save_user_sessions(sessions)

def add_exam_result(user_id: int, exam_result: Dict):
    """Add a new exam result for a user."""
    results = load_exam_results()
    if user_id not in results:
        results[user_id] = []
    results[user_id].append(exam_result)
    save_exam_results(results)

def delete_user_session(user_id: int):
    """Delete a user's session data."""
    sessions = load_user_sessions()
    if user_id in sessions:
        sessions.pop(user_id)
        save_user_sessions(sessions)
        logger.info("Deleted session data for user %s", user_id)

def load_lessons() -> Dict[str, Dict]:
    """Load lesson/study materials database."""
    try:
        if not os.path.exists(LESSON_DB_PATH):
            logger.warning("Lesson database %s not found.", LESSON_DB_PATH)
            return {}
        with open(LESSON_DB_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error("Error loading lesson database: %s", e)
        return {}