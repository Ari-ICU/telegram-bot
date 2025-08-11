import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, ContextTypes

from .storage import load_exam_database, get_user_session, load_user_sessions, save_user_sessions, load_exam_results, save_exam_results

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_GRADE, SELECTING_SUBJECT, PREPARING_EXAM, TAKING_EXAM = range(4)

async def start_exam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start an exam session based on callback data in Khmer."""
    query = update.callback_query
    await query.answer()

    # Step 1: Validate and parse callback data
    try:
        logger.info("Processing callback: %s", query.data)
        if not query.data.startswith("exam_"):
            raise ValueError(f"Invalid prefix in callback: {query.data}")

        payload = query.data[len("exam_"):]  # Remove 'exam_' prefix
        parts = payload.split("_")

        if parts[0].isdigit():
            grade_id = parts[0]
            subject_id = "_".join(parts[1:])
        elif parts[0].lower() == "grade" and len(parts) >= 3 and parts[1].isdigit():
            grade_id = parts[1]
            subject_id = "_".join(parts[2:])
        else:
            raise ValueError(f"Unexpected grade format in callback: {query.data}")

        db_grade_id = f"grade_{grade_id}"
        logger.info("Parsed grade_id: %s, db_grade_id: %s, subject_id: %s", grade_id, db_grade_id, subject_id)
    except AttributeError as e:
        logger.error("Callback data is invalid or missing: %s", str(e))
        await query.message.reply_text(
            f"⚠️ កំហុសប្រព័ន្ធ៖ ទិន្នន័យហៅត្រឡប់មិនត្រឹមត្រូវ។ សូមព្យាយាមម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE
    except (IndexError, ValueError) as e:
        logger.error("Invalid callback format: %s, error: %s", query.data, str(e))
        await query.message.reply_text(
            f"⚠️ ការជ្រើសរើសការប្រឡងមិនត្រឹមត្រូវ៖ {query.data}។ សូមព្យាឯមម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    # Step 2: Load exam database
    try:
        exam_db = load_exam_database()
        logger.info("Available grades: %s", list(exam_db.keys()))
        if not exam_db:
            logger.error("Exam database is empty")
            await query.message.reply_text(
                f"⚠️ កំហុសប្រព័ន្ធ៖ គ្មានការប្រឡងអាចប្រើបានទេ។ សូមព្យាយាមម្តងទៀតនៅពេលក្រោយ។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
            )
            return SELECTING_GRADE
    except Exception as e:
        logger.error("Failed to load exam database: %s", str(e))
        await query.message.reply_text(
            f"⚠️ កំហុសប្រព័ន្ធ៖ មិនអាចផ្ទុកទិន្នន័យការប្រឡងបានទេ។ សូមព្យាឯមម្តងទៀតនៅពេលក្រោយ។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    # Step 3: Validate grade and subject
    grade_data = exam_db.get(db_grade_id)
    if not grade_data:
        logger.error("Grade %s not found in exam database", db_grade_id)
        await query.message.reply_text(
            f"⚠️ មិនអាចរកឃើញថ្នាក់ '{grade_id}'។ សូមជ្រើសរើសថ្នាក់ត្រឹមត្រូវ។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    exam_data = grade_data.get('subjects', {}).get(subject_id)
    if not exam_data:
        logger.error("Exam not found for grade %s, subject %s", db_grade_id, subject_id)
        await query.message.reply_text(
            f"⚠️ មិនអាចរកឃើញការប្រឡងសម្រាប់ថ្នាក់ '{grade_id}' និងមុខវិជ្ជា '{subject_id}'។ សូមជ្រើសរើសការប្រឡងត្រឹមត្រូវ។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    # Step 4: Manage user session
    user_id = update.effective_user.id
    try:
        session = get_user_session(user_id)
        logger.debug("Current session for user %s: %s", user_id, session)
        if session.get("exam_active", False):
            await query.message.reply_text(
                f"⚠️ អ្នកកំពុងប្រឡងរួចហើយ។ សូមបញ្ចប់ ឬបញ្ឈប់ការប្រឡងជាមុនសិន។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
            )
            return SELECTING_GRADE

        session.update({
            "current_grade": grade_id,
            "current_subject": subject_id,
            "current_question": 0,
            "answers": [],
            "start_time": datetime.now().timestamp(),
            "exam_active": True
        })

        sessions = load_user_sessions()
        sessions[user_id] = session
        save_user_sessions(sessions)
        logger.info("Updated session for user %s: %s", user_id, session)
    except Exception as e:
        logger.error("Session management error for user %s: %s", user_id, str(e))
        await query.message.reply_text(
            f"⚠️ កំហុសប្រព័ន្ធ៖ មិនអាចចាប់ផ្តើមវគ្គប្រឡងបានទេ។ សូមព្យាយាមម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    # Step 5: Display exam details
    duration = exam_data.get('duration', 'N/A')
    description = exam_data.get('description', 'គ្មានការពិពណ៌នា')
    grade_title = grade_data.get('title', 'ថ្នាក់មិនស្គាល់')
    text = (
        f"📝 <b>ការប្រឡង៖ {exam_data.get('title', 'ការប្រឡងគ្មានចំណងជើង')}</b>\n"
        f"📚 <b>ថ្នាក់៖ {grade_title}</b>\n\n"
        f"ℹ️ <b>ការពិពណ៌នា៖</b> {description}\n"
        f"⏱️ <b>រយៈពេល៖</b> {duration} នាទី\n"
        f"❓ <b>សំណួរ៖</b> {len(exam_data.get('questions', []))}\n\n"
        f"តើអ្នកត្រៀមខ្លួនចាប់ផ្តើមការប្រឡងហើយឬនៅ?"
    )

    keyboard = [
        [InlineKeyboardButton("✅ ចាប់ផ្តើមការប្រឡង", callback_data=f'begin_{grade_id}_{subject_id}')],
        [InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]
    ]

    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except Exception as e:
        logger.error("Error displaying exam %s for user %s: %s", subject_id, user_id, str(e))
        await query.message.reply_text(
            f"⚠️ កំហុសប្រព័ន្ធ៖ មិនអាចបង្ហាញការប្រឡងបានទេ។ សូមព្យាឯមម្តងទៀត�। [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    return PREPARING_EXAM

async def display_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the current question in the exam in Khmer."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.get("exam_active", False):
        await query.message.reply_text(
            f"⚠️ គ្មានការប្រឡងសកម្ម។ សូមចាប់ផ្តើមការប្រឡងថ្មី។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE
    
    grade_id = session.get("current_grade")
    subject_id = session.get("current_subject")
    db_grade_id = f'grade_{grade_id}'
    logger.info("Displaying question for grade_id: %s, db_grade_id: %s, subject_id: %s", grade_id, db_grade_id, subject_id)
    
    exam_db = load_exam_database()
    logger.info("Available grades: %s", list(exam_db.keys()))
    exam_data = exam_db.get(db_grade_id, {}).get('subjects', {}).get(subject_id)
    
    if not exam_data:
        logger.error("Exam data not found for grade %s, subject %s", db_grade_id, subject_id)
        await query.message.reply_text(
            f"⚠️ មិនអាចរកឃើញទិន្នន័យការប្រឡងសម្រាប់ថ្នាក់ '{grade_id}' និងមុខវិជ្ជា '{subject_id}'។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    questions = exam_data.get('questions', [])
    current_question_idx = session["current_question"]
    
    if current_question_idx >= len(questions):
        return await end_exam(update, context, "បញ្ចប់")
    
    question_data = questions[current_question_idx]
    question_number = current_question_idx + 1
    total_questions = len(questions)
    
    text = (
        f"❓ <b>សំណួរទី {question_number}/{total_questions}</b>\n\n"
        f"{question_data['question']}\n\n"
        f"ជ្រើសរើសចម្លើយ៖"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{chr(65+i)}. {opt}", callback_data=f'answer_{i}') for i, opt in enumerate(question_data['options'])]
    ]
    keyboard.append([InlineKeyboardButton("🏁 បញ្ចប់ការប្រឡង", callback_data='end_exam')])
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except Exception as e:
        logger.error("Error displaying question %d for user %s: %s", current_question_idx, user_id, e)
        await query.message.reply_text(
            f"⚠️ មានកំហុសកើតឡើង។ សូមព្យាឯមម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
    
    return TAKING_EXAM

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user's answer and move to the next question in Khmer."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.get("exam_active", False):
        await query.message.reply_text(
            f"⚠️ គ្មានការប្រឡងសកម្ម។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE
    
    grade_id = session.get("current_grade")
    subject_id = session.get("current_subject")
    db_grade_id = f'grade_{grade_id}'
    logger.info("Handling answer for grade_id: %s, db_grade_id: %s, subject_id: %s", grade_id, db_grade_id, subject_id)
    
    exam_db = load_exam_database()
    logger.info("Available grades: %s", list(exam_db.keys()))
    exam_data = exam_db.get(db_grade_id, {}).get('subjects', {}).get(subject_id)
    
    if not exam_data:
        logger.error("Exam data not found for grade %s, subject %s", db_grade_id, subject_id)
        await query.message.reply_text(
            f"⚠️ មិនអាចរកឃើញទិន្នន័យការប្រឡងសម្រាប់ថ្នាក់ '{grade_id}' និងមុខវិជ្ជា '{subject_id}'។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE
    
    current_question_idx = session["current_question"]
    questions = exam_data.get('questions', [])
    
    if current_question_idx >= len(questions):
        return await end_exam(update, context, "បញ្ចប់")
    
    try:
        answer_idx = int(query.data.replace('answer_', ''))
        session["answers"].append(answer_idx)
        session["current_question"] += 1
    except (IndexError, ValueError):
        logger.error("Invalid answer callback data: %s", query.data)
        await query.message.reply_text(
            f"⚠️ ចម្លើយមិនត្រឹមត្រូវ�। សូមព្យាឯមម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]"
        )
        return TAKING_EXAM

    sessions = load_user_sessions()
    sessions[user_id] = session
    save_user_sessions(sessions)
    
    return await display_question(update, context)

async def end_exam(update: Update, context: ContextTypes.DEFAULT_TYPE, reason: str = "បញ្ចប់"):
    """End the exam and display results in Khmer."""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.get("exam_active", False):
        if query:
            await query.message.reply_text(
                f"⚠️ គ្មានការប្រឡងសកម្ម។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
            )
        return ConversationHandler.END
    
    grade_id = session.get("current_grade")
    subject_id = session.get("current_subject")
    db_grade_id = f'grade_{grade_id}'
    logger.info("Ending exam for grade_id: %s, db_grade_id: %s, subject_id: %s", grade_id, db_grade_id, subject_id)
    
    exam_db = load_exam_database()
    logger.info("Available grades: %s", list(exam_db.keys()))
    grade_data = exam_db.get(db_grade_id, {})
    exam_data = grade_data.get('subjects', {}).get(subject_id)
    
    if not exam_data:
        if query:
            logger.error("Exam data not found for grade %s, subject %s", db_grade_id, subject_id)
            await query.message.reply_text(
                f"⚠️ មិនអាចរកឃើញទិន្នន័យការប្រឡងសម្រាប់ថ្នាក់ '{grade_id}' និងមុខវិជ្ជា '{subject_id}'។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
            )
        return ConversationHandler.END
    
    questions = exam_data.get('questions', [])
    answers = session["answers"]
    
    correct = sum(1 for i, ans in enumerate(answers) if i < len(questions) and ans == questions[i]["correct"])
    total = len(answers)
    score = (correct / total * 100) if total > 0 else 0
    
    results = load_exam_results()
    if user_id not in results:
        results[user_id] = []
    
    result = {
        "grade_id": grade_id,
        "subject_id": subject_id,
        "exam_title": f"{grade_data.get('title', 'ថ្នាក់មិនស្គាល់')} - {exam_data.get('title', 'ការប្រឡងគ្មានចំណងជើង')}",
        "score": score,
        "correct": correct,
        "total": total,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "answers": answers
    }
    results[user_id].append(result)
    save_exam_results(results)
    
    session.update({
        "current_grade": None,
        "current_subject": None,
        "current_question": 0,
        "answers": [],
        "start_time": None,
        "exam_active": False
    })
    
    sessions = load_user_sessions()
    sessions[user_id] = session
    save_user_sessions(sessions)
    
    text = (
        f"🏁 <b>ការប្រឡងបញ្ចប់</b>\n\n"
        f"📝 <b>ការប្រឡង៖</b> {result['exam_title']}\n"
        f"🎯 <b>ពិន្ទុ៖</b> {score:.1f}% ({correct}/{total} ត្រឹមត្រូវ)\n"
        f"📅 <b>កាលបរិច្ឆេទ៖</b> {result['date']}\n\n"
        f"ហេតុផលនៃការបញ្ចប់៖ {reason}\n"
        f"តើអ្នកចង់ពិនិត្យចម្លើយរបស់អ្នក ឬត្រឡប់ទៅម៉ឺនុយដើមទេ?"
    )
    
    keyboard = [
        [InlineKeyboardButton("📋 ពិនិត្យចម្លើយ", callback_data=f'review_{len(results[user_id])-1}')],
        [InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]
    ]
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except Exception as e:
        logger.error("Error ending exam for user %s: %s", user_id, e)
        await query.message.reply_text(
            f"⚠️ មានកំហុសកើតឡើង។ សូមព្យាឯមម្តងទៀត�। [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
    
    return ConversationHandler.END

async def review_exam_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display detailed exam results with explanations in Khmer."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    try:
        result_idx = int(query.data.replace('review_', ''))
    except (IndexError, ValueError):
        logger.error("Invalid review callback data: %s", query.data)
        await query.message.reply_text(
            f"⚠️ សំណើពិនិត្យឡើងវិញមិនត្រឹមត្រូវ។ [Error ID: ERR_{int(datetime.now().timestamp())}]"
        )
        return ConversationHandler.END
    
    results = load_exam_results()
    if user_id not in results or result_idx >= len(results[user_id]):
        logger.error("Result not found for user %s, result_idx %d", user_id, result_idx)
        await query.message.reply_text(
            f"⚠️ មិនអាចរកឃើញលទ្ធផល។ សូមព្យាឯមម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return ConversationHandler.END
    
    result = results[user_id][result_idx]
    grade_id = result.get("grade_id")
    subject_id = result.get("subject_id")
    db_grade_id = f'grade_{grade_id}'
    logger.info("Reviewing exam for grade_id: %s, db_grade_id: %s, subject_id: %s", grade_id, db_grade_id, subject_id)
    
    exam_db = load_exam_database()
    logger.info("Available grades: %s", list(exam_db.keys()))
    grade_data = exam_db.get(db_grade_id, {})
    exam_data = grade_data.get('subjects', {}).get(subject_id)

    if not exam_data:
        logger.error("Exam data not found for grade %s, subject %s", db_grade_id, subject_id)
        await query.message.reply_text(
            f"⚠️ មិនអាចរកឃើញទិន្នន័យការប្រឡងសម្រាប់ថ្នាក់ '{grade_id}' និងមុខវិជ្ជា '{subject_id}'�। [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
        return ConversationHandler.END
    
    questions = exam_data.get('questions', [])
    answers = result["answers"]
    
    text = (
        f"📋 <b>ពិនិត្យការប្រឡង៖ {result['exam_title']}</b>\n\n"
        f"🎯 <b>ពិន្ទុ៖</b> {result['score']:.1f}% ({result['correct']}/{result['total']} ត្រឹមត្រូវ)\n"
        f"📅 <b>កាលបរិច្ឆេទ៖</b> {result['date']}\n\n"
        f"<b>លម្អិតចម្លើយ៖</b>\n"
    )
    
    for i, (q, ans) in enumerate(zip(questions, answers)):
        correct = q["correct"]
        status = "✅ ត្រឹមត្រូវ" if ans == correct else "❌ មិនត្រឹមត្រូវ"
        text += (
            f"❓ <b>សំណួរទី {i+1}:</b> {q['question']}\n"
            f"📝 <b>ចម្លើយរបស់អ្នក៖</b> {q['options'][ans]}\n"
            f"✅ <b>ចម្លើយត្រឹមត្រូវ៖</b> {q['options'][correct]}\n"
            f"ℹ️ <b>ការពន្យល់៖</b> {q.get('explanation', 'គ្មានការពន្យល់')}\n"
            f"{status}\n\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')],
        [InlineKeyboardButton("🎯 ធ្វើការប្រឡងមួយទៀត", callback_data='take_exam')]
    ]
    
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except Exception as e:
        logger.error("Error displaying review for user %s: %s", user_id, e)
        await query.message.reply_text(
            f"⚠️ មានកំហុសកើតឡើង។ សូមព្យាឯមម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]])
        )
    
    return ConversationHandler.END