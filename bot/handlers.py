"""
Telegram bot handlers for user commands and interactions.
Implements /start, /help, /analyze, /watchlist and trading session flow.
"""

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from bot.session_manager import SessionManager
from config.settings import settings
from core.analysis_engine import AnalysisEngine
from ai.prompt_builder import PromptBuilder
from ai.gemini_client import GeminiClient
from utils.logger import get_logger
from utils.helpers import (
    parse_capital_input, validate_capital, format_currency,
    is_market_open_wib, get_next_market_open_time,
    is_stock_related_question, clean_markdown
)

logger = get_logger(__name__)


class BotHandlers:
    """Command and message handlers for Telegram bot."""
    
    @staticmethod
    async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        try:
            user_id = update.effective_user.id
            user_name = update.effective_user.first_name
            
            welcome_text = f"""Halo {user_name}! 👋

Saya adalah AI Trading Assistant untuk Indonesian Stock Market (IHSG).

Saya bisa membantu Anda dengan:
📈 Analisis teknis dan rekomendasi saham
💡 Deteksi sinyal trading (MA20, RSI, Volume)
💰 Perhitungan risk management otomatis
📊 Trading session pagi setiap hari kerja

Gunakan perintah di bawah untuk mulai:
/help    - Lihat bantuan lengkap
/analyze - Mulai sesi analisis
/watchlist - Lihat watchlist saya

Jam trading: 09:00 - 15:30 WIB"""
            
            await update.message.reply_text(welcome_text)
            logger.info(f"User {user_id} started bot")
        
        except Exception as e:
            logger.error(f"Error in handle_start: {e}")
            await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi.")
    
    @staticmethod
    async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        try:
            help_text = """<b>📖 PANDUAN PENGGUNAAN</b>

<b>PERINTAH UTAMA:</b>
/start     - Tampilkan ucapan sambutan
/help      - Tampilkan bantuan ini
/analyze   - Mulai analisis trading
/watchlist - Lihat daftar saham terpantau

<b>ALUR TRADING PAGI (08:00 WIB Hari Kerja):</b>
1. Bot akan mengirim pesan "Masukkan modal trading hari ini"
2. Kirimkan jumlah modal (contoh: "5juta" atau "5000000")
3. Bot akan melakukan screening otomatis
4. AI akan menganalisis dan memberikan rekomendasi
5. Anda akan menerima rekomendasi dengan analisis lengkap

<b>FORMAT REKOMENDASI:</b>
📈 STOCK RECOMMENDATION
Stock: BBCA
Reason: Strong accumulation breakout
Entry: 9500
Target: 9900
Cut Loss: 9300

<b>Money Management:</b>
Allocated Capital: Rp2,000,000
Recommended Lots: 2 lots

<b>CATATAN:</b>
- Modal minimum: Rp {settings.TRADING_CAPITAL_MIN:,}
- Modal maksimum: Rp {settings.TRADING_CAPITAL_MAX:,}
- Alokasi per saham: {settings.ALLOCATION_PERCENTAGE*100:.0f}%
- Sesi auto-expire: {settings.SESSION_TIMEOUT_MINUTES} menit
- Market jam kerja: 09:00-15:30 WIB

Pertanyaan lain? Tanya saja!"""
            
            await update.message.reply_text(help_text, parse_mode="HTML")
        
        except Exception as e:
            logger.error(f"Error in handle_help: {e}")
            await update.message.reply_text("❌ Terjadi kesalahan.")
    
    @staticmethod
    async def handle_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command - start trading session."""
        try:
            user_id = update.effective_user.id
            
            # Check if market is open
            if not is_market_open_wib():
                next_open = get_next_market_open_time()
                next_open_str = next_open.strftime("%d-%m-%Y %H:%M WIB")
                
                msg = f"""⏰ Pasar sedang tutup.

Market jam: 09:00 - 15:30 WIB
Hari kerja: Senin - Jumat

Pasar akan buka pada: {next_open_str}

💡 Tips: Sesi trading otomatis dimulai setiap hari kerja pukul 08:00 WIB."""
                
                await update.message.reply_text(msg)
                return
            
            # Check if session already exists
            existing = SessionManager.get_session(user_id)
            if existing:
                msg = f"""Anda sudah punya sesi aktif.
Modal: {format_currency(existing.capital)}

Ketik /analyze lagi untuk analisis baru, atau tunggu sesi expire."""
                await update.message.reply_text(msg)
                return
            
            # Ask for capital
            msg = f"""📊 Mulai Sesi Trading Analysis

Masukkan modal trading Anda hari ini:
- Minimum: {format_currency(settings.TRADING_CAPITAL_MIN)}
- Maksimum: {format_currency(settings.TRADING_CAPITAL_MAX)}

Contoh input:
• 5juta
• 2500000
• 10.5juta"""
            
            context.user_data['awaiting_capital'] = True
            context.user_data['session_started'] = False

            await update.message.reply_text(msg)
            logger.info(f"User {user_id} started /analyze")
        
        except Exception as e:
            logger.error(f"Error in handle_analyze: {e}")
            await update.message.reply_text("❌ Terjadi kesalahan.")
    
    @staticmethod
    async def handle_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /watchlist command."""
        try:
            await update.message.chat.send_action(ChatAction.TYPING)
            watchlist_text = await AnalysisEngine.run_watchlist_workflow()
            await update.message.reply_text(
                watchlist_text,
                parse_mode="HTML"
            )
        
        except Exception as e:
            logger.error(f"Error in handle_watchlist: {e}")
            await update.message.reply_text("❌ Terjadi kesalahan.")
    
    @staticmethod
    async def handle_capital_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle capital amount input during trading session."""
        try:
            user_id = update.effective_user.id
            text = update.message.text
            
            # Parse capital input
            capital = parse_capital_input(text)
            if capital is None:
                await update.message.reply_text(
                    "❌ Format tidak valid. Contoh: 5juta atau 5000000"
                )
                return
            
            # Validate capital
            valid, message = validate_capital(
                capital,
                settings.TRADING_CAPITAL_MIN,
                settings.TRADING_CAPITAL_MAX
            )
            
            if not valid:
                await update.message.reply_text(f"❌ {message}")
                return
            
            # Create session
            session = SessionManager.create_session(user_id, capital)
            
            msg = f"""✅ Sesi trading dimulai!

Modal: {format_currency(capital)}
Alokasi per saham: {format_currency(int(capital * settings.ALLOCATION_PERCENTAGE))}

🔄 Sedang melakukan screening saham...
⏳ Silakan tunggu (biasanya 30-60 detik)"""
            
            await update.message.reply_text(msg)
            await update.message.chat.send_action(ChatAction.TYPING)
            
            # Store context for analysis
            context.user_data['trading_capital'] = capital
            context.user_data['awaiting_capital'] = False
            context.user_data['session_started'] = True
            
            logger.info(f"Capital input received: user={user_id}, capital={capital}")

            analysis_text = await AnalysisEngine.run_analysis_workflow(user_id, capital)
            await update.message.reply_text(analysis_text, parse_mode="HTML")
            SessionManager.end_session(user_id)
        
        except Exception as e:
            logger.error(f"Error in handle_capital_input: {e}")
            await update.message.reply_text("❌ Terjadi kesalahan memproses modal.")
    
    @staticmethod
    async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general text messages."""
        try:
            user_id = update.effective_user.id
            text = update.message.text.strip()
            
            # Check if user is currently entering capital for /analyze
            if context.user_data.get('awaiting_capital', False):
                capital = parse_capital_input(text)
                if capital is None:
                    await update.message.reply_text(
                        "❌ Format tidak valid. Contoh: 5juta atau 5000000"
                    )
                    return

                await BotHandlers.handle_capital_input(update, context)
                return

            if not is_stock_related_question(text):
                await update.message.reply_text(
                    "❌ Maaf, saya hanya bisa membalas pertanyaan seputar saham dan trading. "
                    "Silakan gunakan /help atau /analyze untuk memulai."
                )
                return

            await update.message.chat.send_action(ChatAction.TYPING)
            prompt = PromptBuilder.build_casual_chat_prompt(text)
            response = await GeminiClient.generate_response(prompt)

            if response:
                clean = clean_markdown(response)
                await update.message.reply_text(clean)
            else:
                await update.message.reply_text(
                    "❌ Maaf, saya belum bisa menjawab saat ini. Silakan coba lagi nanti."
                )
        
        except Exception as e:
            logger.error(f"Error in handle_text_message: {e}")
