"""Tiny page-object helpers for the React UI (selectors rely on ids / visible text, not on CSS classes)."""
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from helpers import BASE_URL, wait_for_otp


def sign_in(driver, wait, email, password):
    driver.get(f"{BASE_URL}/login")
    started = time.time()
    wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[normalize-space()='Continue']").click()
    otp_input = wait.until(EC.presence_of_element_located((By.ID, "otp")))
    otp_input.send_keys(wait_for_otp(email, started))
    driver.find_element(By.XPATH, "//button[contains(., 'Verify and sign in')]").click()


def sign_out(driver, wait):
    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Sign out']"))).click()
    wait.until(EC.presence_of_element_located((By.ID, "email")))


def heading(driver, wait, text):
    return wait.until(EC.visibility_of_element_located((By.XPATH, f"//h1[contains(., '{text}')]")))
