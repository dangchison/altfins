# -*- coding: utf-8 -*-
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_NUM_COLUMNS = 9


def extract_rows(driver: webdriver.Chrome, num_rows: int = 2) -> list[list[str]]:
    """
    Wait for the Vaadin async grid to be fully rendered and return
    `num_rows` rows as lists of cell text values.
    """
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "nis-async-grid"))
        )

        def all_rows_ready(d: webdriver.Chrome) -> bool:
            try:
                cells = (
                    d.find_element(By.CLASS_NAME, "nis-async-grid")
                    .find_elements(By.TAG_NAME, "vaadin-grid-cell-content")
                )
                if len(cells) < num_rows * _NUM_COLUMNS:
                    return False
                for i in range(num_rows):
                    text = cells[i * _NUM_COLUMNS + 3].text.strip()
                    if not text or text == "Asset Name":
                        return False
                return True
            except Exception:
                return False

        WebDriverWait(driver, 30).until(all_rows_ready)
        print("✅ Grid rendered — extracting rows.")

        table = driver.find_element(By.CLASS_NAME, "nis-async-grid")
        cells = table.find_elements(By.TAG_NAME, "vaadin-grid-cell-content")

        rows: list[list[str]] = []
        for i in range(num_rows):
            start = i * _NUM_COLUMNS
            row_data = [
                cell.text.strip()
                for cell in cells[start : start + _NUM_COLUMNS - 1]
            ]
            rows.append(row_data)

        return rows

    except Exception as exc:
        print(f"❌ Grid extraction error: {exc}")
        return []


def click_inspect_button(driver: webdriver.Chrome, row_index: int) -> None:
    """Click the 'Inspect' button for the given (0-based) row."""
    try:
        time.sleep(2)
        buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "altfins-inspect-btn"))
        )

        visible = [b for b in buttons if _is_displayed(b)]
        visible.sort(key=lambda b: b.location.get("y", 0))

        if row_index >= len(visible):
            print(f"❌ Inspect button not found for row {row_index + 1}. "
                  f"Visible: {len(visible)}")
            return

        btn = visible[row_index]
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
        time.sleep(2)

        try:
            ActionChains(driver).move_to_element(btn).click().perform()
        except Exception:
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)

        print(f"✅ Clicked inspect button for row {row_index + 1}.")
        time.sleep(5)  # Wait for popup to render

    except Exception as exc:
        print(f"❌ Inspect button error: {exc}")


def extract_popup_text(driver: webdriver.Chrome) -> str:
    """Return the full text content of the visible trade-setup popup."""
    try:
        popup = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "curated-chart-detail"))
        )
        WebDriverWait(driver, 15).until(
            lambda d: len(
                d.find_element(By.CLASS_NAME, "curated-chart-detail").text.strip()
            ) > 50
        )
        text = popup.text.strip()
        print("✅ Popup text extracted.")
        return text

    except Exception as exc:
        print(f"❌ Popup text extraction failed: {exc}")
        driver.save_screenshot("error_popup_data.png")
        return ""


def extract_popup_image(driver: webdriver.Chrome) -> str:
    """Return the src URL of the chart image inside the popup."""
    try:
        img = WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.CLASS_NAME, "fullscreen-image"))
        )
        src = img.get_attribute("src")
        print("✅ Popup image extracted.")
        return src or ""

    except Exception as exc:
        print(f"❌ Popup image extraction failed: {exc}")
        return ""


def close_popup(driver: webdriver.Chrome) -> None:
    """Close the active popup via overlay click or Escape key."""
    try:
        try:
            overlay = driver.find_element(By.TAG_NAME, "vaadin-dialog-overlay")
            driver.execute_script("arguments[0].click();", overlay)
        except Exception:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)

        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "curated-chart-detail"))
        )
        print("✅ Popup closed.")
        time.sleep(3)  # Vaadin grid needs time to re-render after overlay detach

    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_displayed(element) -> bool:
    try:
        return element.is_displayed()
    except Exception:
        return False
