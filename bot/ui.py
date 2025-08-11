import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ConversationHandler, ContextTypes

from .storage import load_exam_database

logger = logging.getLogger(__name__)

# Conversation states
SELECTING_GRADE, SELECTING_SUBJECT, PREPARING_EXAM, TAKING_EXAM = range(4)

def get_main_menu():
    """Main menu in Khmer."""
    keyboard = [
        [
            InlineKeyboardButton("🎓 ចូលប្រឡង", callback_data='take_exam'),
            InlineKeyboardButton("📊 មើលលទ្ធផល", callback_data='view_results')
        ],
        [
            InlineKeyboardButton("📚 សម្ភារៈសិក្សា", callback_data='study_materials'),
            InlineKeyboardButton("⏰ កាលវិភាគប្រឡង", callback_data='exam_schedule')
        ],
        [
            InlineKeyboardButton("👤 ប្រវត្តិរូប", callback_data='profile'),
            InlineKeyboardButton("❓ ជំនួយ និងការគាំទ្រ", callback_data='help')
        ],
        [InlineKeyboardButton("⚙️ ការកំណត់", callback_data='settings')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with main menu in Khmer."""
    user = update.effective_user
    current_time = datetime.now().strftime("%H:%M")
    
    text = (
        f"🎓 <b>ប្រព័ន្ធគ្រប់គ្រងប្រឡងសាលា</b>\n\n"
        f"សូមស្វាគមន៍មកកាន់ <b>{user.first_name}</b>! 👋\n"
        f"🕒 ពេលវេលាបច្ចុប្បន្ន: {current_time}\n\n"
        f"📚 <b>មុខងារដែលអាចប្រើបាន:</b>\n"
        f"• ប្រឡងអន្តរកម្មជាមួយការផ្ដល់មតិយោបល់ភ្លាមៗ\n"
        f"• ការតាមដានលទ្ធផល និងវិភាគលម្អិត\n"
        f"• សម្ភារៈសិក្សា និងការរៀបចំសម្រាប់ប្រឡង\n"
        f"• ព័ត៌មានចំពោះការអនុវត្ត និងសំណើសម្រាប់ការកែលម្អ\n\n"
        f"សូមជ្រើសរើសជម្រើសខាងក្រោមដើម្បីចាប់ផ្តើម:"
    )
    
    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=get_main_menu(), parse_mode='HTML'
            )
    except Exception as e:
        logger.error("Failed to send/edit main menu: %s", e)
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text, reply_markup=get_main_menu(), parse_mode='HTML'
            )
    return ConversationHandler.END

async def take_exam_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display available grades in Khmer."""
    text = (
        "🎓 <b>ថ្នាក់ដែលអាចប្រឡងបាន</b>\n\n"
        "សូមជ្រើសរើសថ្នាក់ ដើម្បីមើលមុខវិជ្ជាដែលអាចប្រឡងបាន។"
    )

    
    keyboard = []
    exam_db = load_exam_database()
    if not exam_db:
        text = (
            "⚠️ <b>មិនមានការប្រឡង</b>\n\n"
            "បច្ចុប្បន្ននេះមិនមានការប្រឡងទេ។ សូមពិនិត្យមើលម្តងទៀតនៅពេលក្រោយ ឬទាក់ទងការគាំទ្រ។"
        )
        keyboard = [[InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]]
    else:
        for grade_id, grade_data in exam_db.items():
            clean_grade_id = grade_id.replace('grade_', '')
            button_text = grade_data.get('title', 'ថ្នាក់គ្មានចំណងជើង')
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f'grade_{clean_grade_id}')])
    
    keyboard.append([InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.error("Error displaying exam menu: %s", e)
    
    return SELECTING_GRADE

async def show_subjects_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display subjects in Khmer for the selected grade."""
    query = update.callback_query
    await query.answer()

    try:
        logger.info("Processing callback: %s", query.data)

        if query.data.startswith('grade_'):
            grade_id = query.data[len('grade_'):]
        else:
            grade_id = query.data

        if not grade_id.isdigit():
            raise ValueError(f"Invalid grade ID extracted: {grade_id}")

        db_grade_id = f'grade_{grade_id}'
        logger.info("Selected grade_id: %s, db_grade_id: %s", grade_id, db_grade_id)
    except (AttributeError, ValueError) as e:
        logger.error("Invalid callback data: %s, error: %s", query.data, str(e))
        await query.message.reply_text(
            f"⚠️ ជម្រើសថ្នាក់មិនត្រឹមត្រូវ: {query.data}។ សូមសាកល្បងម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    try:
        exam_db = load_exam_database()
        logger.info("Available grades: %s", list(exam_db.keys()))
    except Exception as e:
        logger.error("Failed to load exam database: %s", str(e))
        await query.message.reply_text(
            f"⚠️ បញ្ហាបច្ចេកទេស: មិនអាចទាញទិន្នន័យប្រឡងបានទេ។ សូមសាកល្បងម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    grade_data = exam_db.get(db_grade_id)
    if not grade_data:
        logger.error("Grade %s not found in exam database", db_grade_id)
        await query.message.reply_text(
            f"⚠️ មិនមានថ្នាក់ '{grade_id}' នៅក្នុងប្រព័ន្ធទេ។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    subjects = grade_data.get('subjects')
    if not subjects:
        logger.error("No subjects found for grade %s", db_grade_id)
        await query.message.reply_text(
            f"⚠️ មិនមានមុខវិជ្ជាសម្រាប់ {grade_data.get('title', 'ថ្នាក់នេះ')} ទេ។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    text = (
        f"📚 <b>{grade_data.get('title', 'ថ្នាក់គ្មានចំណងជើង')} - មុខវិជ្ជា</b>\n\n"
        "សូមជ្រើសរើសមុខវិជ្ជា ដើម្បីមើលព័ត៌មានប្រឡង និងចាប់ផ្តើម:"
    )

    keyboard = []
    for subject_id, subject_data in subjects.items():
        button_text = f"{subject_data.get('title', 'មុខវិជ្ជាគ្មានចំណងជើង')} ({subject_data.get('duration', 'N/A')} នាទី)"
        callback_data = f'exam_{grade_id}_{subject_id}'
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        logger.info("Generated subject callback: %s", callback_data)

    keyboard.append([InlineKeyboardButton("⬅️ ត្រឡប់ទៅថ្នាក់", callback_data='take_exam')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.error("Error displaying subjects menu for grade %s: %s", db_grade_id, str(e))
        await query.message.reply_text(
            f"⚠️ បញ្ហាបច្ចេកទេស: មិនអាចបង្ហាញមុខវិជ្ជាបានទេ។ សូមសាកល្បងម្តងទៀត។ [Error ID: ERR_{int(datetime.now().timestamp())}]",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]])
        )
        return SELECTING_GRADE

    return SELECTING_SUBJECT
