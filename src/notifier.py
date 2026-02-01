"""
Elite Sniper v2.0 - Telegram Notifier
Enhanced with screenshot support and rate limiting
"""

import time
import logging
import requests
from typing import Optional
from .config import Config

logger = logging.getLogger("EliteSniperV2.Notifier")

# Rate limiting
_last_message_time = 0
_message_interval = 1.0  # Minimum seconds between messages


def _check_rate_limit() -> bool:
    """Check if we can send a message (rate limiting)"""
    global _last_message_time
    now = time.time()
    if now - _last_message_time < _message_interval:
        return False
    _last_message_time = now
    return True


def send_alert(message: str, parse_mode: str = "HTML") -> bool:
    """
    Send text message to Telegram
    
    Args:
        message: Message text
        parse_mode: "HTML" or "Markdown"
    
    Returns:
        Success status
    """
    if not Config.TELEGRAM_TOKEN or not Config.TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram not configured")
        return False
    
    if not _check_rate_limit():
        logger.debug("Rate limited, skipping message")
        return False
    
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": Config.TELEGRAM_CHAT_ID, 
        "text": message,
        "parse_mode": parse_mode
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.debug("📤 Message sent to Telegram")
            return True
        else:
            logger.warning(f"⚠️ Telegram error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram send error: {e}")
        return False


def send_photo(photo_path: str, caption: str = "") -> bool:
    """
    Send photo to Telegram
    
    Args:
        photo_path: Path to image file
        caption: Optional caption
    
    Returns:
        Success status
    """
    if not Config.TELEGRAM_TOKEN or not Config.TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram not configured")
        return False
    
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendPhoto"
    data = {
        "chat_id": Config.TELEGRAM_CHAT_ID, 
        "caption": caption[:1024]  # Telegram caption limit
    }
    
    try:
        with open(photo_path, "rb") as image_file:
            files = {"photo": image_file}
            response = requests.post(url, data=data, files=files, timeout=30)
            
        if response.status_code == 200:
            logger.debug("📤 Photo sent to Telegram")
            return True
        else:
            logger.warning(f"⚠️ Telegram photo error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram photo error: {e}")
        return False


def send_document(doc_path: str, caption: str = "") -> bool:
    """
    Send document to Telegram
    
    Args:
        doc_path: Path to document file
        caption: Optional caption
    
    Returns:
        Success status
    """
    if not Config.TELEGRAM_TOKEN or not Config.TELEGRAM_CHAT_ID:
        logger.warning("⚠️ Telegram not configured")
        return False
    
    url = f"https://api.telegram.org/bot{Config.TELEGRAM_TOKEN}/sendDocument"
    data = {
        "chat_id": Config.TELEGRAM_CHAT_ID, 
        "caption": caption[:1024]
    }
    
    try:
        with open(doc_path, "rb") as doc_file:
            files = {"document": doc_file}
            response = requests.post(url, data=data, files=files, timeout=30)
            
        if response.status_code == 200:
            logger.debug("📤 Document sent to Telegram")
            return True
        else:
            logger.warning(f"⚠️ Telegram document error: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram document error: {e}")
        return False


def send_status_update(
    session_id: str,
    status: str,
    stats: dict = None,
    mode: str = "PATROL"
) -> bool:
    """
    Send formatted status update
    
    Args:
        session_id: Current session ID
        status: Status message
        stats: Optional statistics dict
        mode: Current operational mode
    """
    emoji_map = {
        "PATROL": "🔍",
        "WARMUP": "⏳",
        "PRE_ATTACK": "⚙️",
        "ATTACK": "🔥",
        "SUCCESS": "🏆"
    }
    
    emoji = emoji_map.get(mode, "📊")
    
    message = f"{emoji} <b>Elite Sniper v2.0</b>\n"
    message += f"└ Session: <code>{session_id[:20]}...</code>\n"
    message += f"└ Mode: {mode}\n"
    message += f"└ Status: {status}\n"
    
    if stats:
        message += f"\n📊 Stats:\n"
        message += f"└ Scans: {stats.get('scans', 0)}\n"
        message += f"└ Days Found: {stats.get('days_found', 0)}\n"
        message += f"└ Slots Found: {stats.get('slots_found', 0)}\n"
        message += f"└ Captchas: {stats.get('captchas_solved', 0)}/{stats.get('captchas_failed', 0)}\n"
    
    return send_alert(message)


def send_success_notification(
    session_id: str,
    worker_id: int,
    screenshot_path: Optional[str] = None
) -> bool:
    """
    Send success notification with optional screenshot
    
    Args:
        session_id: Session ID
        worker_id: Worker that achieved success
        screenshot_path: Optional path to success screenshot
    """
    message = (
        f"🎉🏆 <b>VICTORY! APPOINTMENT SECURED!</b> 🏆🎉\n\n"
        f"✅ Elite Sniper v2.0 has successfully booked an appointment!\n"
        f"📍 Worker: #{worker_id}\n"
        f"🆔 Session: <code>{session_id}</code>\n"
        f"⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"<b>Check your email for confirmation!</b>"
    )
    
    # Send text message first
    send_alert(message)
    
    # Send screenshot if available
    if screenshot_path:
        send_photo(screenshot_path, "🏆 SUCCESS SCREENSHOT")
    
    return True


def send_error_notification(
    session_id: str,
    error: str,
    worker_id: Optional[int] = None
) -> bool:
    """
    Send error notification
    
    Args:
        session_id: Session ID
        error: Error message
        worker_id: Optional worker ID
    """
    worker_str = f"Worker #{worker_id}" if worker_id else "System"
    
    message = (
        f"🚨 <b>ERROR</b>\n"
        f"└ {worker_str}\n"
        f"└ {error[:200]}\n"
        f"└ Session: <code>{session_id[:20]}...</code>"
    )
    
    return send_alert(message)