from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler
from bot.ui import send_main_menu, take_exam_menu, show_subjects_menu
from bot.exam import start_exam, display_question, handle_answer, end_exam, review_exam_details, SELECTING_GRADE, SELECTING_SUBJECT, PREPARING_EXAM, TAKING_EXAM
from bot.storage import load_exam_results, get_user_session, load_user_sessions, save_user_sessions, load_lessons
import logging
from datetime import datetime
import time


logger = logging.getLogger(__name__)
lessons_db = load_lessons()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with user registration."""
    user = update.effective_user
    logger.info("ប្រព័ន្ធការប្រឡងបានចាប់ផ្តើមដោយអ្នកប្រើ %s (%s)", user.id, user.username or user.first_name)
    
    results = load_exam_results()
    if user.id not in results:
        results[user.id] = []
        from bot.storage import save_exam_results
        save_exam_results(results)
        
    return await send_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced help system."""
    text = (
        "❓ <b>មជ្ឈមណ្ឌលជំនួយ និងគាំទ្រ</b>\n\n"
        "🎓 <b>របៀបប្រើប្រាស់ប្រព័ន្ធនេះ:</b>\n"
        "1. ជ្រើសរើស 'ធ្វើការប្រឡង' ដើម្បីចាប់ផ្តើមការវាយតម្លៃ\n"
        "2. ជ្រើសមុខវិជ្ជារបស់អ្នក និងអានសេចក្តីណែនាំ\n"
        "3. ឆ្លើយសំណួរផ្ទៀងផ្ទាត់ក្នុងរយៈពេលកំណត់\n"
        "4. ពិនិត្យលទ្ធផល និងការពន្យល់\n"
        "5. តាមដានមុខងារនៅក្នុង 'មើលលទ្ធផល'\n\n"
        "📚 <b>បញ្ជីពាក្យបញ្ជា:</b>\n"
        "• /start - មុខងារមេនយូ\n"
        "• /help - មជ្ឈមណ្ឌលជំនួយនេះ\n"
        "• /profile - មើលប្រវត្តិរូបរបស់អ្នក\n"
        "• /results - មើលលទ្ធផលដោយរហ័ស\n"
        "• /clear - សម្អាតប្រវត្តិសន្ទនា\n\n"
        "🆘 <b>ត្រូវការជំនួយបន្ថែម?</b>\n"
        "• អ៊ីមែល: support@mgmtschool.edu\n"
        "• ទូរស័ព្ទ: +1 (555) 123-4567\n"
        "• ម៉ោងការិយាល័យ: ច័ន្ទ-សុក្រ 9ព្រឹក-5ល្ងាច\n\n"
        "💡 <b>គន្លឹះសម្រាប់ជោគជ័យ:</b>\n"
        "• អានសំណួរយ៉ាងប្រុងប្រយ័ត្ន\n"
        "• គ្រប់គ្រងពេលវេលារបស់អ្នកឲ្យមានប្រសិទ្ធភាព\n"
        "• ពិនិត្យការពន្យល់បន្ទាប់ពីការប្រឡង\n"
        "• អនុវត្តជាប្រចាំដើម្បីទទួលបានលទ្ធផលល្អ"
    )
    
    keyboard = [
        [InlineKeyboardButton("📖 មគ្គុទេសក៍សិក្សា", callback_data='study_materials')],
        [InlineKeyboardButton("🎯 ធ្វើការប្រឡង", callback_data='take_exam')],
        [InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]
    ]
    
    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        elif update.callback_query:
            await update.callback_query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
            )
    except Exception as e:
        logger.error("កំហុសនៅ help_command: %s", e)

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced clear command with session reset."""
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    user_id = update.effective_user.id

    sessions = load_user_sessions()
    if user_id in sessions:
        sessions[user_id] = {
            "current_exam": None,
            "current_question": 0,
            "answers": [],
            "start_time": None,
            "exam_active": False
        }
        from bot.storage import save_user_sessions
        save_user_sessions(sessions)
    
    context.user_data.clear()
    logger.info("សម្អាតទិន្នន័យសម័យសម្រាប់អ្នកប្រើ %s", user_id)

    deleted = 0
    for offset in range(0, 8):
        try:
            mid = message_id - offset
            if mid > 0:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
                deleted += 1
        except Exception:
            pass

    logger.info("អ្នកប្រើ %s បានសម្អាតសន្ទនា។ %d សារត្រូវបានលុប។", user_id, deleted)
    return await send_main_menu(update, context)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick profile command."""
    user = update.effective_user
    user_id = user.id
    results = load_exam_results()
    
    if results:
        avg_score = sum(r["score"] for r in results.get(user_id, [])) / len(results.get(user_id, [])) if results.get(user_id, []) else 0
        best_score = max((r["score"] for r in results.get(user_id, [])), default=0)
        total_exams = len(results.get(user_id, []))
        subjects_taken = len(set(r["exam_id"] for r in results.get(user_id, [])))
    else:
        avg_score = best_score = total_exams = subjects_taken = 0
    
    text = (
        f"👤 <b>ប្រវត្តិសិស្ស</b>\n\n"
        f"👋 <b>ឈ្មោះ:</b> {user.first_name} {user.last_name or ''}\n"
        f"🆔 <b>លេខអ្នកប្រើ:</b> {user_id}\n"
        f"📧 <b>ឈ្មោះអ្នកប្រើ:</b> @{user.username or 'មិនបានកំណត់'}\n\n"
        f"📊 <b>សមត្ថភាពសិក្សា:</b>\n"
        f"• ចំនួនការប្រឡងសរុប: <b>{total_exams}</b>\n"
        f"• មុខវិជ្ជាទទួលបាន: <b>{subjects_taken}</b>\n"
        f"• ពិន្ទុមធ្យម: <b>{avg_score:.1f}%</b>\n"
        f"• ពិន្ទុល្អបំផុត: <b>{best_score:.1f}%</b>\n\n"
        f"🎯 <b>គោលដៅសិក្សា:</b>\n"
        f"• បញ្ចប់មុខវិជ្ជាស្នូលទាំងអស់\n"
        f"• សម្រេចបានពិន្ទុមធ្យមលើស ៩០%\n"
        f"• ជំនាញមូលដ្ឋានអាជីវកម្ម"
    )
    
    keyboard = [
        [InlineKeyboardButton("📊 មើលលទ្ធផលទាំងអស់", callback_data='view_results')],
        [InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]
    ]
    
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
    )

async def results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick results command."""
    user_id = update.effective_user.id
    results = load_exam_results().get(user_id, [])
    
    if not results:
        text = (
            "📊 <b>លទ្ធផលការប្រឡងរបស់អ្នក</b>\n\n"
            "🔍 មិនមានលទ្ធផលការប្រឡង។\n"
            "សូមធ្វើការប្រឡងដំបូងរបស់អ្នកដើម្បីមើលលទ្ធផលនៅទីនេះ!\n\n"
            "🎓 ត្រៀមខ្លួនសម្រាប់ការសិក្សា?"
        )
        keyboard = [
            [InlineKeyboardButton("🎯 ធ្វើការប្រឡងដំបូង", callback_data='take_exam')],
            [InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]
        ]
    else:
        total_exams = len(results)
        avg_score = sum(r["score"] for r in results) / total_exams
        best_score = max(r["score"] for r in results)
        recent_results = results[-5:]
        
        text = (
            f"📊 <b>ផ្ទាំងគ្រប់គ្រងលទ្ធផលការប្រឡងរបស់អ្នក</b>\n\n"
            f"🎯 <b>ស្ថិតិទូទៅ:</b>\n"
            f"• ចំនួនការប្រឡងសរុប: <b>{total_exams}</b>\n"
            f"• ពិន្ទុមធ្យម: <b>{avg_score:.1f}%</b>\n"
            f"• ពិន្ទុល្អបំផុត: <b>{best_score:.1f}%</b>\n"
            f"• ការប្រឡងចុងក្រោយ: {results[-1]['date'][:10]}\n\n"
            f"📈 <b>លទ្ធផលថ្មីៗ:</b>\n"
        )
        
        for i, result in enumerate(recent_results):
            date = result["date"][:10]
            text += f"• {result['exam_title']}: <b>{result['score']:.1f}%</b> ({date})\n"
        
        keyboard = []
        for i, result in enumerate(results[-3:]):
            idx = len(results) - len(results[-3:]) + i
            keyboard.append([InlineKeyboardButton(
                f"📋 ពិនិត្យឡើងវិញ: {result['exam_title'][:20]}...", 
                callback_data=f'review_{idx}'
            )])
        
        keyboard.extend([
            [InlineKeyboardButton("📊 ប្រវត្តិពេញលេញ", callback_data='full_history')],
            [InlineKeyboardButton("⬅️ ត្រឡប់ទៅមេនុយ", callback_data='main_menu')]
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    except Exception as e:
        logger.error("កំហុសក្នុងការបង្ហាញលទ្ធផល: %s", e)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced button handler for all UI interactions."""
    query = update.callback_query
    await query.answer()

    if not query.data:
        return

    try:
        if query.data == 'main_menu':
            return await send_main_menu(update, context)
        elif query.data == 'take_exam':
            return await take_exam_menu(update, context)
        elif query.data == 'view_results':
            return await results_command(update, context)
        elif query.data == 'help':
            return await help_command(update, context)
        elif query.data == 'exam_schedule':
            text = (
                "⏰ <b>ព័ត៌មានកាលវិភាគការប្រឡង</b>\n\n"
                "📅 <b>ការប្រឡងខាងមុខ:</b>\n"
                "• ថ្នាក់ទី ១: មានស្រាប់\n"
                "• ថ្នាក់ទី ២: មានស្រាប់\n"
                "• ថ្នាក់ទី ៣: មានស្រាប់\n"
                "• ថ្នាក់ទី ៤: មានស្រាប់\n"
                "• ថ្នាក់ទី ៥: មានស្រាប់\n"
                "• ថ្នាក់ទី ៦: មានស្រាប់\n"
                "• ថ្នាក់ទី ៧: មានស្រាប់\n"
                "• ថ្នាក់ទី ៨: មានស្រាប់\n"
                "• ថ្នាក់ទី ៩: មានស្រាប់\n"
                "• ថ្នាក់ទី ១០: មានស្រាប់\n"
                "• ថ្នាក់ទី ១៧: មានស្រាប់\n"
                "• ថ្នាក់ទី ១២: មានស្រាប់\n\n"
                "🕐 <b>ម៉ោងដំណើរការ:</b>\n"
                "• ច័ន្ទ - សុក្រ: ២៤ ម៉ោង\n"
                "• សៅរ៍ - អាទិត្យ: ២៤ ម៉ោង\n\n"
                "⚡ ការប្រឡងទាំងអស់អាចធ្វើបានគ្រប់ពេល!"
            )
            keyboard = [
                [InlineKeyboardButton("🎯 ធ្វើការប្រឡងឥឡូវនេះ", callback_data='take_exam')],
                [InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        elif query.data.startswith('exam_'):
            return await start_exam(update, context)
        elif query.data.startswith('begin_'):
            session = get_user_session(update.effective_user.id)
            session["start_time"] = time.time()
            sessions = load_user_sessions()
            sessions[update.effective_user.id] = session
            save_user_sessions(sessions)
            return await display_question(update, context)
        elif query.data.startswith('answer_'):
            return await handle_answer(update, context)
        elif query.data == 'end_exam':
            return await end_exam(update, context, "ended")
        elif query.data == 'study_materials':
            text = (
                "📚 <b>ជ្រើសរើសថ្នាក់រៀនសម្រាប់ធនធានសិក្សា</b>\n\n"
                "សូមជ្រើសរើសថ្នាក់រៀន៖"
            )
            keyboard = []
            for grade_num in sorted(lessons_db):
                grade_title = lessons_db[grade_num].get("title", f"ថ្នាក់ទី {grade_num}")
                keyboard.append([InlineKeyboardButton(grade_title, callback_data=f'study_grade_{grade_num}')])
            keyboard.append([InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        elif query.data == 'profile':
            return await profile_command(update, context)
        elif query.data == 'settings':
            text = (
                "⚙️ <b>ការកំណត់ និងចំណង់ចំណូលចិត្ត</b>\n\n"
                "🔧 <b>ការកំណត់ការប្រឡង:</b>\n"
                "• ការជូនដំណឹង: ✅ បើក\n"
                "• សម្លេង: ✅ បើក\n"
                "• ដាក់សំណើរដោយស្វ័យប្រវត្តិពេលពេលវេលាសម័យ: ✅ បើក\n"
                "• បង្ហាញការពន្យល់: ✅ បើក\n\n"
                "🌍 <b>ភាសា និងតំបន់:</b>\n"
                "• ភាសា: ភាសាខ្មែរ\n"
                "• ម៉ោងតំបន់: កំណត់ដោយស្វ័យប្រវត្តិ\n\n"
                "📊 <b>ការកំណត់ភាពឯកជន:</b>\n"
                "• ចែករំលែកលទ្ធផល: 🔒 ឯកជន\n"
                "• វិភាគសមត្ថភាព: ✅ បើក"
            )
            keyboard = [
                [InlineKeyboardButton("🔔 ការកំណត់ការជូនដំណឹង", callback_data='notifications')],
                [InlineKeyboardButton("🌐 ការកំណត់ភាសា", callback_data='language')],
                [InlineKeyboardButton("⬅️ ត្រឡប់ទៅម៉ឺនុយ", callback_data='main_menu')]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        elif query.data.startswith('review_'):
            return await review_exam_details(update, context)
        else:
            return await send_main_menu(update, context)
    except Exception as e:
        logger.error("កំហុសនៅ button_handler: %s", e)
        await query.message.reply_text(
            "⚠️ មានកំហុសកើតឡើង។ សូមព្យាយាមម្តងទៀត។",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 មុខងារមេនុយ", callback_data='main_menu')]])
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced error handler with better user experience."""
    error_id = f"ERR_{int(time.time())}"
    logger.error(
        "កំហុស %s នៅពេលដោះស្រាយ update %s: %s",
        error_id,
        update.update_id if update else "មិនស្គាល់",
        context.error,
        exc_info=context.error
    )
    
    error_message = (
        f"⚠️ <b>កំហុសប្រព័ន្ធ</b>\n\n"
        f"មានកំហុសមួយដែលមិនបានរំពឹងទុក។ ក្រុមបច្ចេកទេសរបស់យើងបានទទួលដំណឹងហើយ។\n\n"
        f"🔍 លេខកំហុស: <code>{error_id}</code>\n"
        f"🕒 ម៉ោង: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"🔄 សូមព្យាយាមម្តងទៀត ឬត្រឡប់ទៅមុខងារមេនុយ។"
    )
    
    try:
        if update and update.message:
            await update.message.reply_text(
                error_message, 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 មុខងារមេនុយ", callback_data='main_menu')]]),
                parse_mode='HTML'
            )
        elif update and update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                error_message,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 មុខងារមេនុយ", callback_data='main_menu')]]),
                parse_mode='HTML'
            )
    except Exception:
        logger.error("បរាជ័យក្នុងការផ្ញើសារកំហុសសម្រាប់កំហុស %s", error_id)

def create_exam_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(take_exam_menu, pattern='^take_exam$')
        ],
        states={
            SELECTING_GRADE: [
                CallbackQueryHandler(show_subjects_menu, pattern="^grade_"),
            ],
            SELECTING_SUBJECT: [
                CallbackQueryHandler(start_exam, pattern="^exam_"),
                CallbackQueryHandler(take_exam_menu, pattern="^take_exam$"),
            ],
            PREPARING_EXAM: [
                CallbackQueryHandler(display_question, pattern="^begin_"),
            ],
            TAKING_EXAM: [
                CallbackQueryHandler(handle_answer, pattern="^answer_"),
                CallbackQueryHandler(lambda u, c: end_exam(u, c, "ended"), pattern="^end_exam$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(send_main_menu, pattern="^main_menu$"),
        ],
        allow_reentry=True,
    )
