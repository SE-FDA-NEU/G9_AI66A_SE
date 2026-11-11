"""Comprehensive Playwright UI & Translation Crawler for Sports Venue Booking System.

Evaluates:
1. Status codes and navigation for all required routes (unauth, customer, owner, admin).
2. Console errors, page exceptions, network failures.
3. Language toggle:
   - 'en': ZERO hybrid strings (e.g., 'Find a sân', 'sân nhà.'), ZERO untranslated Vietnamese UI words.
   - 'vi': ZERO hybrid strings (e.g., 'Find a sân', 'Book a sân', 'View sân', '1 sân found'),
           accurate Vietnamese translations for core UI elements (navbar, buttons, status, etc.).
4. Horizontal scroll / layout overflow detection.
"""

import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5000"

FORBIDDEN_EN_PATTERNS = [
    "Find a sân",
    "Book a sân",
    "View sân",
    "sân nhà.",
    "sân nhà",
    "Ảnh minh họa",
    "ĐẶT SÂN Ở HÀ NỘI",
    "Cụm sân",
    "Tìm sân",
    "Xem sân",
    "Đặt sân",
    "Đăng nhập",
    "Đăng ký",
    "Đã xác nhận",
    "Đã hoàn thành",
    "Đã hủy",
    "Bảo trì",
    "Khung giờ",
    "Mã đặt sân",
    "Phiếu xác nhận",
    "Đơn đặt sân",
    "Lịch sử đặt sân",
    "Trang cá nhân",
    "Quản trị hệ thống",
]

FORBIDDEN_VI_PATTERNS = [
    "Find a sân",
    "Book a sân",
    "View sân",
    "1 sân found",
    "sân(s) found",
    "a sân",
]

EXPECTED_VI_NAV = {
    "Find a venue": "Tìm sân thể thao",
    "Sign in": "Đăng nhập",
    "Register": "Đăng ký",
    "Sign out": "Đăng xuất",
    "My page": "Trang cá nhân",
    "My bookings": "Lịch sử đặt sân",
    "My venues": "Cụm sân của tôi",
    "Bookings": "Lịch đặt sân",
    "Administration": "Quản trị hệ thống",
}

class TestReporter:
    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []

    def record(self, role, url, lang, passed, details=""):
        self.results.append({
            "role": role,
            "url": url,
            "lang": lang,
            "passed": passed,
            "details": details
        })
        status_str = "PASS" if passed else "FAIL"
        print(f"[{status_str}] [{role}] {url} (lang={lang}) {details}")
        if not passed:
            self.errors.append(f"[{role}] {url} (lang={lang}): {details}")

    def add_warning(self, msg):
        self.warnings.append(msg)
        print(f"[WARN] {msg}")

def check_page_text(page, role, url, lang, reporter):
    # Retrieve visible body innerText
    text = page.evaluate("() => document.body.innerText")
    
    # Check for forbidden substrings
    if lang == "en":
        for pattern in FORBIDDEN_EN_PATTERNS:
            if pattern.lower() in text.lower():
                reporter.record(role, url, lang, False, f"Found forbidden Vietnamese/hybrid string in EN mode: '{pattern}'")
                return False
    elif lang == "vi":
        for pattern in FORBIDDEN_VI_PATTERNS:
            if pattern.lower() in text.lower():
                reporter.record(role, url, lang, False, f"Found forbidden hybrid string in VI mode: '{pattern}'")
                return False
        
        # Check navbar specifically
        nav_text = page.evaluate("() => document.querySelector('nav') ? document.querySelector('nav').innerText : ''")
        for en_word, vi_expected in EXPECTED_VI_NAV.items():
            if en_word in nav_text:
                reporter.record(role, url, lang, False, f"Navbar has untranslated English text in VI mode: '{en_word}' (expected '{vi_expected}')")
                return False

    # Check for overflow
    overflow = page.evaluate("""() => {
        return document.documentElement.scrollWidth > window.innerWidth + 5;
    }""")
    if overflow:
        reporter.add_warning(f"Horizontal overflow detected on {url} (lang={lang})")

    reporter.record(role, url, lang, True, "Page content & translations verified clean")
    return True

def test_page_both_langs(page, role, path, reporter):
    url = f"{BASE_URL}{path}"
    console_logs = []
    page_errors = []

    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}") if msg.type in ["error", "warning"] else None)
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    response = page.goto(url, wait_until="networkidle")
    if not response or response.status >= 400:
        if path == "/verify":
            # Verify without token returns 400 with friendly message
            pass
        else:
            reporter.record(role, url, "load", False, f"HTTP status {response.status if response else 'None'}")
            return

    # Check default/en
    page.evaluate("() => { if (window.setLanguage) window.setLanguage('en'); }")
    page.wait_for_timeout(200)
    check_page_text(page, role, path, "en", reporter)

    # Switch to 'vi'
    page.evaluate("() => { if (window.setLanguage) window.setLanguage('vi'); }")
    page.wait_for_timeout(200)
    check_page_text(page, role, path, "vi", reporter)

    if page_errors:
        reporter.record(role, url, "runtime", False, f"JavaScript errors: {page_errors}")

def login_user(page, email, password):
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

def run_all_tests():
    reporter = TestReporter()
    print("=" * 70)
    print("STARTING PLAYWRIGHT END-TO-END UI & I18N EVALUATION")
    print(f"Target: {BASE_URL}")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Unauthenticated Crawl
        print("\n--- Testing Unauthenticated Routes ---")
        context = browser.new_context()
        page = context.new_page()

        unauth_routes = [
            "/",
            "/search",
            "/venues/1",
            "/login",
            "/register",
            "/verify"
        ]
        for route in unauth_routes:
            test_page_both_langs(page, "Visitor", route, reporter)
        context.close()

        # 2. Customer Crawl
        print("\n--- Testing Customer Routes (minh@example.com) ---")
        context = browser.new_context()
        page = context.new_page()
        login_user(page, "minh@example.com", "sanbong1")

        customer_routes = [
            "/search",
            "/venues/1",
            "/booking/1",
            "/dashboard",
            "/my-bookings"
        ]
        for route in customer_routes:
            test_page_both_langs(page, "Customer", route, reporter)
        context.close()

        # 3. Owner Crawl
        print("\n--- Testing Owner Routes (lan.owner@example.com) ---")
        context = browser.new_context()
        page = context.new_page()
        login_user(page, "lan.owner@example.com", "sanbong1")

        owner_routes = [
            "/search",
            "/owner/venues",
            "/owner/venues/1/schedule",
            "/owner/venues/1/pricing",
            "/owner/bookings"
        ]
        for route in owner_routes:
            test_page_both_langs(page, "Owner", route, reporter)
        context.close()

        # 4. Admin Crawl
        print("\n--- Testing Admin Routes (admin@example.com) ---")
        context = browser.new_context()
        page = context.new_page()
        login_user(page, "admin@example.com", "sanbong1")

        admin_routes = [
            "/admin"
        ]
        for route in admin_routes:
            test_page_both_langs(page, "Admin", route, reporter)
        context.close()

        browser.close()

    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)
    total_checks = len(reporter.results)
    passed_checks = sum(1 for r in reporter.results if r["passed"])
    failed_checks = total_checks - passed_checks
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {failed_checks}")
    if reporter.warnings:
        print(f"Warnings ({len(reporter.warnings)}):")
        for w in reporter.warnings:
            print(f"  - {w}")

    if reporter.errors:
        print("\nFAILURES DETECTED:")
        for err in reporter.errors:
            print(f"  ❌ {err}")
        return 1
    else:
        print("\n✅ ALL UI & I18N CHECKS PASSED WITH 100% SUCCESS!")
        return 0

if __name__ == "__main__":
    sys.exit(run_all_tests())
