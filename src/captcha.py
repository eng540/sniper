"""
Elite Sniper v2.0 - Enhanced Captcha System
Integrates KingSniperV12 safe captcha checking with pre-solving capability
"""

import time
import logging
from typing import Optional, List, Tuple
from playwright.sync_api import Page

logger = logging.getLogger("EliteSniperV2.Captcha")

# Try to import ddddocr
try:
    import ddddocr
    DDDDOCR_AVAILABLE = True
except ImportError:
    DDDDOCR_AVAILABLE = False
    logger.warning("⚠️ ddddocr not available - captcha solving disabled")


class EnhancedCaptchaSolver:
    """
    Enhanced captcha solver with:
    - Multiple selector attempts (from KingSniperV12)
    - Safe checking without failures
    - Black captcha detection
    - Pre-solving capability
    - Session-aware solving
    """
    
    def __init__(self):
        """Initialize OCR engine"""
        self.ocr = None
        self._pre_solved_code: Optional[str] = None
        self._pre_solved_time: float = 0.0
        self._pre_solve_timeout: float = 30.0  # Pre-solved code expires after 30s
        
        if DDDDOCR_AVAILABLE:
            try:
                self.ocr = ddddocr.DdddOcr(beta=True)
                logger.info("✅ Captcha solver initialized (beta mode)")
            except Exception as e:
                logger.error(f"❌ Captcha solver init failed: {e}")
                self.ocr = None
        else:
            logger.warning("⚠️ ddddocr not installed - run: pip install ddddocr")
    
    def safe_captcha_check(self, page: Page, location: str = "GENERAL") -> Tuple[bool, bool]:
        """
        Safe captcha presence check (from KingSniperV12)
        
        Returns:
            (has_captcha: bool, check_successful: bool)
        """
        try:
            # Step 1: Check page content for captcha keywords
            page_content = page.content().lower()
            
            captcha_keywords = [
                "captcha", 
                "security code", 
                "verification", 
                "human check",
                "verkaptxt"  # German sites
            ]
            
            has_captcha_text = any(keyword in page_content for keyword in captcha_keywords)
            
            if not has_captcha_text:
                logger.debug(f"[{location}] No captcha keywords found")
                return False, True
            
            # Step 2: Search for captcha input (multiple selectors)
            captcha_selectors = self._get_captcha_selectors()
            
            for selector in captcha_selectors:
                try:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        logger.info(f"🔍 [{location}] Captcha found: {selector}")
                        return True, True
                except:
                    continue
            
            # Found keywords but no input field
            logger.debug(f"[{location}] Captcha text found but no input field")
            return False, True
            
        except Exception as e:
            logger.error(f"[{location}] Captcha check error: {e}")
            return False, False
    
    def verify_captcha_solved(self, page: Page, location: str = "VERIFY") -> Tuple[bool, str]:
        """
        Verify if captcha was successfully solved and we're on the next page
        
        Returns:
            (success: bool, page_type: str)
            page_type: CAPTCHA_PAGE, CALENDAR_PAGE, TIME_SLOTS_PAGE, FORM_PAGE, SUCCESS_PAGE, UNKNOWN
        """
        import time as time_module
        
        # Wait for page to stabilize (max 3 retries)
        for attempt in range(3):
            try:
                # Wait for page to be ready
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=3000)
                except:
                    pass
                
                content = page.content().lower()
                
                # Check if still on captcha page
                has_captcha_input = page.locator("input[name='captchaText']").count() > 0
                
                if has_captcha_input:
                    return False, "CAPTCHA_PAGE"
                
                # Check for calendar page indicators
                calendar_indicators = [
                    "please select a date",
                    "appointments are available",
                    "appointment_showday",
                    "no appointments",
                    "keine termine"
                ]
                if any(ind in content for ind in calendar_indicators):
                    return True, "CALENDAR_PAGE"
                
                # Check for time slots page
                time_indicators = [
                    "please select an appointment",
                    "book this appointment",
                    "appointment_showform"
                ]
                if any(ind in content for ind in time_indicators):
                    return True, "TIME_SLOTS_PAGE"
                
                # Check for booking form page
                form_indicators = [
                    "new appointment",
                    "appointment_newappointmentform",
                    "appointment_addappointment"
                ]
                if any(ind in content for ind in form_indicators):
                    return True, "FORM_PAGE"
                
                # Check for success page
                success_indicators = [
                    "appointment number",
                    "confirmation",
                    "successfully"
                ]
                if any(ind in content for ind in success_indicators):
                    return True, "SUCCESS_PAGE"
                
                return False, "UNKNOWN"
                
            except Exception as e:
                if attempt < 2:
                    time_module.sleep(0.5)
                    continue
                logger.error(f"[{location}] Verification error: {e}")
                return False, "ERROR"
        
        return False, "TIMEOUT"
    
    def _get_captcha_selectors(self) -> List[str]:
        """
        Get list of possible captcha selectors
        From KingSniperV12 with additions
        """
        return [
            "input[name='captchaText']",
            "input[name='captcha']",
            "input#captchaText",
            "input#captcha",
            "input[type='text'][placeholder*='code']",
            "input[type='text'][placeholder*='Code']",
            "input.verkaptxt",
            "input.captcha-input",
            "input[id*='captcha']",
            "input[name*='captcha']"
        ]
    
    def _get_captcha_image_selectors(self) -> List[str]:
        """Get list of possible captcha image selectors"""
        return [
            "captcha > div",
            "div.captcha-image",
            "div#captcha",
            "img[alt*='captcha']",
            "img[alt*='CAPTCHA']",
            "canvas.captcha"
        ]
    
    def _extract_base64_captcha(self, page: Page, location: str = "EXTRACT") -> Optional[bytes]:
        """
        Extract captcha image from CSS background-image base64 data URL
        This is how the German embassy website embeds captcha images
        
        Returns:
            Image bytes or None if not found
        """
        import base64
        import re
        
        try:
            # Try to find captcha div with base64 background
            captcha_div = page.locator("captcha > div").first
            
            if not captcha_div.is_visible(timeout=2000):
                logger.debug(f"[{location}] Captcha div not visible")
                return None
            
            # Get the style attribute
            style = captcha_div.get_attribute("style")
            
            if not style:
                logger.debug(f"[{location}] No style attribute on captcha div")
                return None
            
            # Extract base64 from: background:white url('data:image/jpg;base64,XXXXX') 
            # Pattern matches the base64 data
            pattern = r"url\(['\"]?data:image/[^;]+;base64,([A-Za-z0-9+/=]+)['\"]?\)"
            match = re.search(pattern, style)
            
            if not match:
                logger.debug(f"[{location}] No base64 pattern found in style")
                return None
            
            base64_data = match.group(1)
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_data)
            
            logger.info(f"[{location}] Extracted captcha from base64 ({len(image_bytes)} bytes)")
            return image_bytes
            
        except Exception as e:
            logger.warning(f"[{location}] Base64 extraction failed: {e}")
            return None
    
    def _get_captcha_image(self, page: Page, location: str = "GET_IMG") -> Optional[bytes]:
        """
        Get captcha image using multiple methods:
        1. First try CSS background base64 extraction (German embassy style)
        2. Fallback to screenshot method
        
        Returns:
            Image bytes or None
        """
        # Method 1: Try base64 extraction first (most reliable for this website)
        image_bytes = self._extract_base64_captcha(page, location)
        if image_bytes:
            return image_bytes
        
        # Method 2: Fallback to screenshot
        for img_selector in self._get_captcha_image_selectors():
            try:
                element = page.locator(img_selector).first
                if element.is_visible(timeout=1000):
                    image_bytes = element.screenshot(timeout=5000)
                    logger.info(f"[{location}] Got captcha via screenshot: {img_selector}")
                    return image_bytes
            except:
                continue
        
        logger.warning(f"[{location}] Could not get captcha image by any method")
        return None
    
    def detect_black_captcha(self, image_bytes: bytes) -> bool:
        """
        Detect poisoned/black captcha
        Black captcha = session is poisoned and needs to be recreated
        
        Black captcha indicators:
        - Very small file size (< 1500 bytes)
        - OCR returns garbage like "4333"
        """
        if len(image_bytes) < 1500:
            logger.critical("[BLACK CAPTCHA] Detected! Size: {} bytes - Session POISONED".format(len(image_bytes)))
            return True
        
        return False
    
    def validate_captcha_result(self, code: str, location: str = "VALIDATE") -> Tuple[bool, str]:
        """
        Validate captcha OCR result
        
        Rules based on German embassy website behavior:
        - 6 characters = VALID (normal captcha)
        - 7-8 characters = WARNING (session aging, too many refreshes)
        - < 4 or > 8 characters = INVALID (likely OCR error)
        - "4333" or similar repeated = BLACK CAPTCHA garbage
        
        Returns:
            (is_valid: bool, status: str)
            status: VALID, AGING, INVALID, BLACK_DETECTED, TOO_SHORT, TOO_LONG
        """
        if not code:
            logger.warning(f"[{location}] Empty captcha code")
            return False, "EMPTY"
        
        # Clean the code
        code = code.strip().replace(" ", "")
        code_len = len(code)
        
        # Detect black captcha garbage patterns
        # Only truly repeated patterns like "4444", "333", "0000" are garbage
        black_patterns = ["4333", "333", "444", "1111", "0000", "4444", "3333"]
        is_all_same = len(set(code)) == 1  # All characters are the same
        if code in black_patterns or is_all_same:
            logger.critical(f"[{location}] BLACK CAPTCHA pattern detected: '{code}'")
            return False, "BLACK_DETECTED"
        
        # Check length
        if code_len < 4:
            logger.warning(f"[{location}] Captcha too short: '{code}' ({code_len} chars)")
            return False, "TOO_SHORT"
        
        if code_len == 6:
            # Perfect! Normal captcha
            logger.info(f"[{location}] Valid 6-char captcha: '{code}'")
            return True, "VALID"
        
        if code_len == 7:
            # Warning - session aging, but still usable
            logger.warning(f"[{location}] 7-char captcha (session aging): '{code}'")
            return True, "AGING_7"
        
        if code_len == 8:
            # Critical warning - session near death
            logger.warning(f"[{location}] 8-char captcha (session near death): '{code}'")
            return True, "AGING_8"
        
        if code_len > 8:
            logger.error(f"[{location}] Captcha too long: '{code}' ({code_len} chars)")
            return False, "TOO_LONG"
        
        # 4-5 chars - REJECT! Embassy requires exactly 6 chars
        # OCR probably missed a character
        if code_len in [4, 5]:
            logger.warning(f"[{location}] OCR incomplete: '{code}' ({code_len} chars) -需要6个字符!")
            return False, "TOO_SHORT"
    def solve(self, image_bytes: bytes, location: str = "SOLVE") -> Tuple[str, str]:
        """
        Solve captcha from image bytes with validation
        
        German embassy captcha ALWAYS has 6 characters.
        If OCR returns less, we retry or reject.
        
        Returns:
            (captcha_code: str, status: str)
            status: VALID, AGING_7, AGING_8, BLACK_DETECTED, TOO_SHORT, etc.
        """
        if not self.ocr:
            logger.error("[OCR] Engine not initialized")
            return "", "NO_OCR"
        
        try:
            # Detect black captcha first (by image size)
            if self.detect_black_captcha(image_bytes):
                return "", "BLACK_IMAGE"
            
            # Try OCR multiple times if result is short
            max_attempts = 3
            best_result = ""
            best_len = 0
            
            for attempt in range(max_attempts):
                # Solve using OCR
                result = self.ocr.predict(image_bytes)
                result = result.replace(" ", "").strip().lower()
                
                # Clean common OCR mistakes
                result = self._clean_ocr_result(result)
                
                current_len = len(result)
                
                # Keep the longest result
                if current_len > best_len:
                    best_result = result
                    best_len = current_len
                
                # If we got 6 chars, that's perfect - stop trying
                if current_len == 6:
                    break
                
                # If we got 7-8 chars (aging), that's acceptable
                if current_len >= 7:
                    break
                
                # Otherwise, try again
                if attempt < max_attempts - 1:
                    logger.debug(f"[{location}] OCR returned {current_len} chars, retrying... ({attempt+1}/{max_attempts})")
                    time.sleep(0.1)  # Small delay before retry
            
            # Use the best result we got
            result = best_result
            
            # Validate the result
            is_valid, status = self.validate_captcha_result(result, location)
            
            if not is_valid:
                logger.warning(f"[{location}] Invalid captcha result: '{result}' - Status: {status}")
                return "", status
            
            logger.info(f"[{location}] Captcha solved: '{result}' - Status: {status}")
            return result, status
            
        except Exception as e:
            logger.error(f"[{location}] Captcha solve error: {e}")
            return "", "ERROR"
    
    def _clean_ocr_result(self, text: str) -> str:
        """
        Clean common OCR mistakes for the German embassy captcha.
        The captcha uses lowercase letters and digits only.
        """
        # Remove any characters that shouldn't be there
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789')
        cleaned = ''.join(c for c in text if c in allowed_chars)
        
        # Common OCR substitution corrections
        # OCR sometimes confuses similar-looking characters
        replacements = {
            'o': '0',  # letter o -> digit 0 (less common in captchas)
            'O': '0',
            'l': '1',  # lowercase L -> digit 1
            'I': '1',  # uppercase I -> digit 1
            'i': '1',  # lowercase i -> digit 1 (if at wrong position)
            's': '5',  # s -> 5
            'S': '5',
            'z': '2',  # z -> 2
            'Z': '2',
            'b': '6',  # b -> 6
            'g': '9',  # g -> 9
        }
        
        # Only apply if result is too short - maybe OCR got confused
        if len(cleaned) < 6:
            # Try alternate interpretations - disabled for now as it might make things worse
            pass
        
        return cleaned
    
    def pre_solve(self, page: Page, location: str = "PRE_SOLVE") -> Tuple[bool, Optional[str], str]:
        """
        Pre-solve captcha for instant submission later
        
        Returns:
            (success: bool, captcha_code: Optional[str], status: str)
        """
        try:
            # Check if captcha exists
            has_captcha, check_ok = self.safe_captcha_check(page, location)
            
            if not check_ok:
                logger.error(f"[{location}] Pre-solve captcha check failed")
                return False, None, "CHECK_FAILED"
            
            if not has_captcha:
                logger.debug(f"[{location}] No captcha to pre-solve")
                return True, None, "NO_CAPTCHA"
            
            # Find captcha image using unified method
            image_bytes = self._get_captcha_image(page, location)
            
            if not image_bytes:
                logger.warning(f"[{location}] Captcha image not found for pre-solve")
                return False, None, "NO_IMAGE"
            
            # Solve captcha with validation
            code, status = self.solve(image_bytes, location)
            
            if not code:
                logger.warning(f"[{location}] Pre-solve failed: {status}")
                return False, None, status
            
            # Cache the solution
            self._pre_solved_code = code
            self._pre_solved_time = time.time()
            self._pre_solved_status = status
            
            logger.info(f"[{location}] Pre-solved captcha: '{code}' - Status: {status}")
            return True, code, status
            
        except Exception as e:
            logger.error(f"[{location}] Pre-solve error: {e}")
            return False, None, "ERROR"
    
    def get_pre_solved(self) -> Optional[str]:
        """
        Get pre-solved captcha code if still valid
        
        Returns:
            Captcha code or None if expired/unavailable
        """
        if not self._pre_solved_code:
            return None
        
        # Check if expired
        age = time.time() - self._pre_solved_time
        if age > self._pre_solve_timeout:
            logger.warning("⏰ Pre-solved captcha expired")
            self._pre_solved_code = None
            return None
        
        return self._pre_solved_code
    
    def clear_pre_solved(self):
        """Clear pre-solved captcha"""
        self._pre_solved_code = None
        self._pre_solved_time = 0.0
    
    def solve_from_page(
        self, 
        page: Page, 
        location: str = "GENERAL",
        timeout: int = 10000
    ) -> Tuple[bool, Optional[str]]:
        """
        Complete captcha solving workflow
        Uses pre-solved code if available
        
        Returns:
            (success: bool, captcha_code: Optional[str], status: str)
        """
        try:
            # Check if captcha exists
            has_captcha, check_ok = self.safe_captcha_check(page, location)
            
            if not check_ok:
                logger.error(f"[{location}] Captcha check failed")
                return False, None, "CHECK_FAILED"
            
            if not has_captcha:
                logger.debug(f"[{location}] No captcha present")
                return True, None, "NO_CAPTCHA"
            
            # Find captcha input field
            input_selector = None
            for selector in self._get_captcha_selectors():
                try:
                    if page.locator(selector).first.is_visible(timeout=1000):
                        input_selector = selector
                        break
                except:
                    continue
            
            if not input_selector:
                logger.warning(f"[{location}] Captcha input not found")
                return False, None, "NO_INPUT"
            
            # Check for pre-solved code first
            code = self.get_pre_solved()
            status = getattr(self, '_pre_solved_status', 'VALID')
            
            if code:
                logger.info(f"[{location}] Using pre-solved captcha: '{code}'")
                self.clear_pre_solved()
            else:
                # Find captcha image using unified method
                image_bytes = self._get_captcha_image(page, location)
                
                if not image_bytes:
                    logger.warning(f"[{location}] Captcha image not found")
                    return False, None, "NO_IMAGE"
                
                # Solve captcha with validation
                code, status = self.solve(image_bytes, location)
                
                if not code:
                    logger.warning(f"[{location}] Solve failed: {status}")
                    return False, None, status
            
            # Fill captcha
            try:
                page.fill(input_selector, code, timeout=3000)
                logger.info(f"[{location}] Captcha filled: '{code}' - Status: {status}")
                return True, code, status
            except Exception as e:
                logger.error(f"[{location}] Failed to fill captcha: {e}")
                return False, None, "FILL_ERROR"
            
        except Exception as e:
            logger.error(f"[{location}] Captcha solving workflow error: {e}")
            return False, None, "ERROR"
    
    def submit_captcha(self, page: Page, method: str = "enter") -> bool:
        """
        Submit captcha (press Enter or click submit)
        
        Args:
            method: "enter" or "click"
        """
        try:
            if method == "enter":
                page.keyboard.press("Enter")
                logger.info("⏎ Captcha submitted (Enter)")
            else:
                # Try to find submit button
                submit_selectors = [
                    "button[type='submit']",
                    "input[type='submit']",
                    "button.submit",
                    "a.submit"
                ]
                
                for selector in submit_selectors:
                    try:
                        button = page.locator(selector).first
                        if button.is_visible(timeout=1000):
                            button.click(timeout=3000)
                            logger.info("🖱️ Captcha submitted (Click)")
                            return True
                    except:
                        continue
                
                # Fallback to Enter
                page.keyboard.press("Enter")
                logger.info("⏎ Captcha submitted (Enter fallback)")
            
            return True
            
        except Exception as e:
            logger.error(f"[CAPTCHA] Submit error: {e}")
            return False
    
    def reload_captcha(self, page: Page, location: str = "RELOAD") -> bool:
        """
        Reload captcha image by clicking "Load another picture" button.
        This is used when captcha solving fails - instead of going back to start,
        we just reload and try again.
        
        Returns:
            True if reload was successful
        """
        try:
            # Selector for reload button
            reload_selectors = [
                "input[name='action:appointment_refreshCaptcha']",
                "#appointment_newAppointmentForm_form_newappointment_refreshcaptcha",
                "input[value='Load another picture']",
                "input[value*='another picture']",
            ]
            
            for selector in reload_selectors:
                try:
                    button = page.locator(selector).first
                    if button.is_visible(timeout=2000):
                        button.click(timeout=3000)
                        logger.info(f"[{location}] Clicked 'Load another picture' - waiting for new captcha...")
                        
                        # Wait for new captcha to load
                        page.wait_for_timeout(1500)  # Allow time for new captcha image
                        
                        return True
                except:
                    continue
            
            logger.warning(f"[{location}] Could not find reload captcha button")
            return False
            
        except Exception as e:
            logger.error(f"[{location}] Reload captcha error: {e}")
            return False
    
    def solve_form_captcha_with_retry(
        self, 
        page: Page, 
        location: str = "FORM_RETRY",
        max_attempts: int = 5
    ) -> Tuple[bool, Optional[str], str]:
        """
        Solve form captcha with retry logic.
        
        IMPORTANT: This method is used specifically for FORM page captcha.
        When captcha solving fails, instead of returning to start,
        it clicks "Load another picture" and tries again.
        
        This is the SMART logic: we don't lose our valuable slot by going back,
        we just reload the captcha and try again until we succeed.
        
        Args:
            page: Playwright page
            location: Log location identifier
            max_attempts: Maximum number of attempts
            
        Returns:
            (success: bool, captcha_code: Optional[str], status: str)
        """
        for attempt in range(max_attempts):
            attempt_num = attempt + 1
            
            logger.info(f"[{location}] Captcha attempt {attempt_num}/{max_attempts}")
            
            # Try to solve
            success, code, status = self.solve_from_page(page, f"{location}_A{attempt_num}")
            
            if success and code:
                # Got a valid solution!
                logger.info(f"[{location}] SUCCESS on attempt {attempt_num}: '{code}'")
                return True, code, status
            
            # Failed - try to reload captcha
            if attempt < max_attempts - 1:  # Don't reload on last attempt
                logger.warning(f"[{location}] Attempt {attempt_num} failed ({status}), reloading captcha...")
                
                if not self.reload_captcha(page, f"{location}_RELOAD"):
                    logger.error(f"[{location}] Could not reload captcha - aborting")
                    return False, None, "RELOAD_FAILED"
                
                # Small delay after reload
                time.sleep(0.5)
        
        # All attempts failed
        logger.error(f"[{location}] All {max_attempts} attempts failed")
        return False, None, "MAX_ATTEMPTS_REACHED"


# Backward compatibility
class CaptchaSolver:
    """Original captcha solver for backward compatibility"""
    
    def __init__(self):
        if DDDDOCR_AVAILABLE:
            self.ocr = ddddocr.DdddOcr(beta=True)
        else:
            self.ocr = None
    
    def solve(self, image_bytes: bytes) -> str:
        if not self.ocr:
            return ""
        try:
            res = self.ocr.predict(image_bytes)
            res = res.replace(" ", "").strip()
            print(f"[AI] Captcha Solved: {res}")
            return res
        except Exception as e:
            print(f"[AI] Error solving captcha: {e}")
            return ""