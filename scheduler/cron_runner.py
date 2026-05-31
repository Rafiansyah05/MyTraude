"""
Scheduler for automated trading analysis.
Handles cron-triggered analysis at specified times.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Coroutine, Any

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class CronRunner:
    """Cron-based scheduler for automated tasks."""
    
    _is_running: bool = False
    _tasks: list = []
    
    @staticmethod
    async def run_daily_at(
        hour: int,
        minute: int,
        func: Callable[[], Coroutine[Any, Any, None]],
        task_name: str = "task"
    ):
        """
        Run async function daily at specified time (WIB timezone).
        
        Args:
            hour: Hour in WIB (0-23)
            minute: Minute (0-59)
            func: Async function to call
            task_name: Task name for logging
        """
        wib_tz = timezone(timedelta(hours=7))
        
        while CronRunner._is_running:
            try:
                # Get next run time
                now = datetime.now(wib_tz)
                next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If time has passed today, schedule for tomorrow
                if now >= next_run:
                    next_run = next_run + timedelta(days=1)
                
                # Skip weekends for trading
                while next_run.weekday() >= 5:  # 5=Saturday, 6=Sunday
                    next_run = next_run + timedelta(days=1)
                
                # Calculate wait time
                wait_seconds = (next_run - now).total_seconds()
                
                logger.info(
                    f"[{task_name}] Scheduled for {next_run.strftime('%Y-%m-%d %H:%M WIB')} "
                    f"(in {wait_seconds/3600:.1f} hours)"
                )
                
                # Wait until execution time
                await asyncio.sleep(wait_seconds)
                
                if not CronRunner._is_running:
                    break
                
                # Execute task
                logger.info(f"[{task_name}] Executing...")
                await func()
                logger.info(f"[{task_name}] Completed")
                
            except asyncio.CancelledError:
                logger.debug(f"[{task_name}] Cancelled")
                break
            except Exception as e:
                logger.error(f"[{task_name}] Error: {e}")
                # Wait before retry
                await asyncio.sleep(60)
    
    @staticmethod
    async def start_scheduler(
        morning_analysis_func: Optional[Callable] = None,
        afternoon_check_func: Optional[Callable] = None
    ):
        """
        Start scheduler with configured tasks.
        
        Args:
            morning_analysis_func: Function to call for morning analysis
            afternoon_check_func: Function to call for afternoon check
        """
        try:
            CronRunner._is_running = True
            logger.info("Starting scheduler...")
            
            # Create tasks
            tasks = []
            
            if morning_analysis_func:
                task = asyncio.create_task(
                    CronRunner.run_daily_at(
                        settings.TRADING_SESSION_HOUR,
                        settings.TRADING_SESSION_MINUTE,
                        morning_analysis_func,
                        "MORNING_ANALYSIS"
                    )
                )
                tasks.append(task)
                logger.info(
                    f"Morning analysis scheduled for {settings.TRADING_SESSION_HOUR}:"
                    f"{settings.TRADING_SESSION_MINUTE:02d} WIB"
                )
            
            if afternoon_check_func:
                task = asyncio.create_task(
                    CronRunner.run_daily_at(
                        14, 30,  # 14:30 WIB (30 mins before market close)
                        afternoon_check_func,
                        "AFTERNOON_CHECK"
                    )
                )
                tasks.append(task)
                logger.info("Afternoon check scheduled for 14:30 WIB")
            
            CronRunner._tasks = tasks
            
            # Wait for all tasks
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            logger.info("Scheduler stopped")
        
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        finally:
            CronRunner._is_running = False
    
    @staticmethod
    async def stop_scheduler():
        """Stop all scheduled tasks."""
        CronRunner._is_running = False
        
        for task in CronRunner._tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        CronRunner._tasks.clear()
        logger.info("Scheduler stopped")


class ScheduledAnalysis:
    """Handle scheduled analysis tasks."""
    
    @staticmethod
    async def morning_analysis(bot_send_func):
        """
        Morning trading analysis task.
        Triggered at 08:00 WIB on weekdays.
        
        Args:
            bot_send_func: Function to send messages to users
        """
        try:
            logger.info("Starting morning analysis...")
            
            # Message to users asking for capital
            analysis_message = """🌅 PAGI! Analisis Trading Hari Ini Dimulai

📊 Mari mulai sesi trading pagi Anda!

Langkah pertama: Masukkan modal trading untuk hari ini

Format:
• Contoh: "5juta" atau "2500000"
• Minimum: Rp 100,000
• Maksimum: Rp 100,000,000

Saya akan segera melakukan screening otomatis dan memberikan rekomendasi dengan entry, target, dan cut loss."""
            
            logger.info(f"Morning analysis message: {analysis_message[:50]}...")
            
            # In production, this would send to all registered users
            # For now, just log
            logger.info("Morning analysis completed")
        
        except Exception as e:
            logger.error(f"Error in morning_analysis: {e}")
    
    @staticmethod
    async def afternoon_check(bot_send_func):
        """
        Afternoon market check task.
        Triggered at 14:30 WIB (30 mins before market close).
        
        Args:
            bot_send_func: Function to send messages to users
        """
        try:
            logger.info("Starting afternoon check...")
            
            check_message = """📋 PENGECEKAN SORE

Pasar akan tutup dalam 1 jam (15:30 WIB).

Review posisi Anda:
✓ Apakah sudah hit target?
✓ Apakah perlu cut loss?
✓ Status atau perubahan tren?

Jangan lupa manage posisi sebelum market tutup!"""
            
            logger.info("Afternoon check completed")
        
        except Exception as e:
            logger.error(f"Error in afternoon_check: {e}")
