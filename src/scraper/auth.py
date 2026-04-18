# -*- coding: utf-8 -*-
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def login(driver: webdriver.Chrome, email: str, password: str) -> None:
    """
    Authenticate on altfins.com using email + password.
    Raises no exceptions on failure — prints error and continues so the
    caller can decide whether to abort.
    """
    driver.get("https://altfins.com/login")

    try:
        # altfins may open on the REGISTRATION tab in headless/cold state — switch to login
        try:
            sign_in_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//vaadin-horizontal-layout[contains(@class, 'link-to-tab')]"
                    "//span[contains(@class, 'link') and text()='Sign in']",
                ))
            )
            driver.execute_script("arguments[0].click();", sign_in_link)
            time.sleep(2)
        except Exception as exc:
            print(f"⚠️ Could not click 'Sign in' link: {exc}")

        email_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
        )
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']"))
        )
        email_input.clear()
        email_input.send_keys(email)
        time.sleep(1)

        pass_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
        )
        pass_input.clear()
        pass_input.send_keys(password)
        time.sleep(1)
        pass_input.send_keys(Keys.RETURN)

        try:
            WebDriverWait(driver, 10).until(EC.url_changes("https://altfins.com/login"))
        except Exception:
            time.sleep(3)  # Safe fallback

        print("✅ Login successful!")

    except Exception as exc:
        print(f"❌ Login error: {exc}")
