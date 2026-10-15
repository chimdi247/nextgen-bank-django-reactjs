"""Browser tests against the real stack (nginx -> Django -> Postgres, Celery, Mailpit). Needs `make up` (and the seeded demo users)."""
import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, BASE_URL, DEMO_PASSWORD, activation_path, unique_email, wait_for_otp
from pages import heading, sign_in, sign_out

pytestmark = pytest.mark.selenium


def test_login_page_renders_and_rejects_a_wrong_password(driver, wait):
    driver.get(f"{BASE_URL}/login")
    wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys("nobody@example.com")
    driver.find_element(By.ID, "password").send_keys("wrong-password")
    driver.find_element(By.XPATH, "//button[normalize-space()='Continue']").click()
    alert = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "[role='alert']")))
    assert alert.text.strip()
    assert "/login" in driver.current_url


def test_unauthenticated_visitors_are_redirected_to_login(driver, wait):
    driver.get(f"{BASE_URL}/transfer")
    wait.until(EC.url_contains("/login"))


def test_admin_signs_in_with_otp_and_sees_the_branch_console(driver, wait):
    sign_in(driver, wait, ADMIN_EMAIL, ADMIN_PASSWORD)
    heading(driver, wait, "Branch overview")
    nav = driver.find_element(By.TAG_NAME, "nav").text
    for item in ("Cash deposit", "KYC verification", "Customers", "System"):
        assert item in nav, f"{item} missing from the staff menu"
    # the system page links to Grafana & friends
    driver.find_element(By.XPATH, "//nav//a[contains(., 'System')]").click()
    heading(driver, wait, "System")
    hrefs = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "main a")]
    assert any("/d/nb-overview" in h for h in hrefs) and any("nb-postgres" in h for h in hrefs)
    sign_out(driver, wait)


def test_admin_deposit_page_looks_up_the_customer(driver, wait):
    sign_in(driver, wait, ADMIN_EMAIL, ADMIN_PASSWORD)
    heading(driver, wait, "Branch overview")
    driver.get(f"{BASE_URL}/staff/deposit")
    heading(driver, wait, "Cash deposit")
    driver.find_element(By.ID, "acct").send_keys("1000110000000015")  # alice (seeded demo data)
    wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "main"), "Alice"))


def test_new_customer_registers_activates_and_signs_in(driver, wait):
    email = unique_email("reg")
    started = time.time()
    driver.get(f"{BASE_URL}/register")
    wait.until(EC.presence_of_element_located((By.ID, "fn"))).send_keys("Selenium")
    driver.find_element(By.ID, "ln").send_keys("Tester")
    driver.find_element(By.ID, "em").send_keys(email)
    driver.find_element(By.ID, "idn").send_keys(str(int(time.time()) % 2_000_000_000))
    driver.find_element(By.ID, "sa").send_keys("blue")
    driver.find_element(By.ID, "pw").send_keys("Str0ng#Passw0rd")
    driver.find_element(By.ID, "pw2").send_keys("Str0ng#Passw0rd")
    driver.find_element(By.XPATH, "//button[normalize-space()='Create account']").click()
    heading(driver, wait, "Check your inbox")

    driver.get(BASE_URL + activation_path(email, started))   # the e-mailed link points at localhost:8080: use the in-network host
    wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Your account is active"))

    sign_in(driver, wait, email, "Str0ng#Passw0rd")
    heading(driver, wait, "Hello, Selenium")
    wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "main"), "do not have a bank account yet"))


def test_customer_sends_money_with_security_question_and_otp(driver, wait):
    """alice -> bob through the real three-step flow (password+OTP login, security answer, transfer OTP)."""
    sign_in(driver, wait, "alice@example.com", DEMO_PASSWORD)
    heading(driver, wait, "Hello, Alice")
    driver.get(f"{BASE_URL}/transfer")
    heading(driver, wait, "Send money")
    to = driver.find_element(By.ID, "to")
    to.send_keys("1000110000000024")                         # bob (seeded demo data)
    wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "main"), "Bob M."))
    driver.find_element(By.ID, "amount").send_keys("1.00")
    driver.find_element(By.ID, "note").send_keys("selenium")
    started = time.time()
    driver.find_element(By.XPATH, "//button[normalize-space()='Continue']").click()
    wait.until(EC.presence_of_element_located((By.ID, "ans"))).send_keys("blue")
    driver.find_element(By.XPATH, "//button[contains(., 'Send me the code')]").click()
    otp_input = wait.until(EC.presence_of_element_located((By.ID, "otp")))
    otp_input.send_keys(wait_for_otp("alice@example.com", started))
    driver.find_element(By.XPATH, "//button[contains(., 'Confirm transfer')]").click()
    wait.until(EC.visibility_of_element_located((By.XPATH, "//h2[contains(., 'Money sent')]")))


def test_customers_cannot_open_staff_pages(driver, wait):
    sign_in(driver, wait, "bob@example.com", DEMO_PASSWORD)
    heading(driver, wait, "Hello, Bob")
    driver.get(f"{BASE_URL}/staff/kyc")
    heading(driver, wait, "Hello, Bob")      # redirected home
