"""
نظام Logging محكم للبوت
يسجل جميع الأحداث والأخطاء بشكل منظم
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import traceback

class BotLogger:
    """نظام تسجيل متقدم"""

    def __init__(self, name: str = 'discord_bot', log_file: str = 'bot.log'):
        self.name = name
        self.log_file = log_file
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """إعداد Logger"""
        # إنشاء logger
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)

        # منع التكرار
        if logger.handlers:
            return logger

        # Format
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console Handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler
        try:
            file_handler = logging.FileHandler(
                self.log_file,
                encoding='utf-8',
                mode='a'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f'⚠️ فشل إنشاء ملف السجل: {e}')

        return logger

    # ==================== Logging Methods ====================

    def info(self, message: str):
        """معلومات عامة"""
        self.logger.info(message)

    def success(self, message: str):
        """نجاح عملية"""
        self.logger.info(f'✅ {message}')

    def warning(self, message: str):
        """تحذير"""
        self.logger.warning(f'⚠️ {message}')

    def error(self, message: str, exc_info: bool = False):
        """خطأ"""
        self.logger.error(f'❌ {message}', exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = True):
        """خطأ حرج"""
        self.logger.critical(f'🔥 {message}', exc_info=exc_info)

    def debug(self, message: str):
        """معلومات للمطورين"""
        self.logger.debug(f'🐛 {message}')

    def exception(self, message: str, exception: Exception):
        """تسجيل استثناء كامل"""
        tb = ''.join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        ))
        self.logger.error(f'❌ {message}\n{tb}')

    # ==================== Specialized Logging ====================

    def command_executed(self, user: str, command: str, guild: str):
        """تسجيل تنفيذ أمر"""
        self.info(f'📝 أمر: /{command} | المستخدم: {user} | السيرفر: {guild}')

    def command_error(self, user: str, command: str, error: str):
        """تسجيل خطأ في أمر"""
        self.error(f'📝 فشل أمر: /{command} | المستخدم: {user} | الخطأ: {error}')

    def event_processed(self, event_name: str, details: str = ''):
        """تسجيل معالجة حدث"""
        msg = f'🎯 حدث: {event_name}'
        if details:
            msg += f' | {details}'
        self.debug(msg)

    def event_error(self, event_name: str, error: str):
        """تسجيل خطأ في حدث"""
        self.error(f'🎯 فشل حدث: {event_name} | الخطأ: {error}')

    def database_query(self, query_type: str, table: str, success: bool = True):
        """تسجيل استعلام قاعدة بيانات"""
        status = '✅' if success else '❌'
        self.debug(f'{status} DB: {query_type} | جدول: {table}')

    def database_error(self, operation: str, error: str):
        """تسجيل خطأ في قاعدة البيانات"""
        self.error(f'💾 DB Error: {operation} | {error}')

    def api_call(self, endpoint: str, success: bool = True):
        """تسجيل استدعاء API"""
        status = '✅' if success else '❌'
        self.debug(f'{status} API: {endpoint}')

    def bot_ready(self, bot_name: str, guilds: int, users: int):
        """تسجيل جاهزية البوت"""
        self.success(f'البوت جاهز: {bot_name} | السيرفرات: {guilds} | الأعضاء: {users}')

    def bot_shutdown(self, reason: str = 'Normal shutdown'):
        """تسجيل إيقاف البوت"""
        self.info(f'⏹️ إيقاف البوت: {reason}')

    def guild_joined(self, guild_name: str, guild_id: str, member_count: int):
        """تسجيل انضمام لسيرفر"""
        self.success(f'انضمام لسيرفر: {guild_name} (ID: {guild_id}) | الأعضاء: {member_count}')

    def guild_left(self, guild_name: str, guild_id: str):
        """تسجيل مغادرة سيرفر"""
        self.warning(f'مغادرة سيرفر: {guild_name} (ID: {guild_id})')

    def moderation_action(self, action: str, target: str, moderator: str, reason: str):
        """تسجيل إجراء إداري"""
        self.info(f'🛡️ {action} | الهدف: {target} | المشرف: {moderator} | السبب: {reason}')

    def security_alert(self, alert_type: str, details: str):
        """تنبيه أمني"""
        self.warning(f'🔐 تنبيه أمني: {alert_type} | {details}')

    # ==================== Performance Logging ====================

    def performance(self, operation: str, duration_ms: float):
        """تسجيل الأداء"""
        if duration_ms > 1000:
            self.warning(f'⏱️ عملية بطيئة: {operation} | المدة: {duration_ms:.2f}ms')
        else:
            self.debug(f'⏱️ {operation} | المدة: {duration_ms:.2f}ms')

    # ==================== Rotation ====================

    def rotate_log(self, max_size_mb: int = 10):
        """تدوير ملف السجل إذا كان كبيراً"""
        try:
            log_path = Path(self.log_file)
            if log_path.exists():
                size_mb = log_path.stat().st_size / (1024 * 1024)
                if size_mb > max_size_mb:
                    # نسخ احتياطي
                    backup_name = f"{self.log_file}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    log_path.rename(backup_name)
                    self.info(f'🔄 تدوير السجل: {backup_name}')
        except Exception as e:
            self.warning(f'فشل تدوير السجل: {e}')

# ==================== Helper Functions ====================

def get_logger(name: str = 'discord_bot') -> BotLogger:
    """الحصول على logger"""
    return BotLogger(name)

# النسخة الافتراضية
bot_logger = BotLogger()