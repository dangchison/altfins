# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from database import save_data_to_supabase

import time

import os
from dotenv import load_dotenv

load_dotenv()

def setup_driver():
  options = webdriver.ChromeOptions()
  options.add_argument("--headless=new")
  options.add_argument("--disable-gpu")
  options.add_argument("--no-sandbox")
  options.add_argument("--disable-dev-shm-usage")
  options.add_argument("--window-size=1920,1080")

  driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
  return driver

def login_with_email(driver, email, password):
  driver.get("https://altfins.com/login")

  try:
    # Under headless mode or cold states, altfins might start on REGISTRATION_TAB
    # Make sure we click the login tab first via JS to bypass any interceptors
    try:
      # Switch to Login form by clicking the "Sign in" link as suggested
      sign_in_link = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "//vaadin-horizontal-layout[contains(@class, 'link-to-tab')]//span[contains(@class, 'link') and text()='Sign in']"))
      )
      driver.execute_script("arguments[0].click();", sign_in_link)
      time.sleep(2)
    except Exception as e:
      print("⚠️ Could not click 'Sign in' link:", str(e))
      pass

    # Vaadin injects native input elements inside or uses Shadow DOM
    email_input = WebDriverWait(driver, 15).until(
      EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
    )
    
    # Ensuring it's interactable
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
    
    # Wait for the URL to change indicating successful login (or fallback)
    try:
      WebDriverWait(driver, 10).until(EC.url_changes("https://altfins.com/login"))
    except Exception:
      time.sleep(3) # safe fallback

    print("✅ Login successful!")
  except Exception as e:
    print("❌ Login error:", str(e))

def load_website(driver, url):
  driver.get(url)
  print("✅ The website has loaded natively, waiting for dynamic elements.")

def extract_table_rows(driver, num_rows=2):
  try:
    # Wait for the grid container
    table = WebDriverWait(driver, 15).until(
      EC.presence_of_element_located((By.CLASS_NAME, "nis-async-grid"))
    )

    num_columns = 9

    # STRICT WAIT: Hold until ALL requested rows have their coin-name cell (column 3)
    # populated. Column 3 of row i lives at cell index (i * num_columns + 3).
    # Wrap in try/except so StaleElementReferenceException returns False instead of
    # propagating — WebDriverWait only ignores NoSuchElementException by default.
    def all_rows_ready(d):
      try:
        cells = d.find_element(By.CLASS_NAME, "nis-async-grid") \
                 .find_elements(By.TAG_NAME, "vaadin-grid-cell-content")
        if len(cells) < num_rows * num_columns:
          return False
        for i in range(num_rows):
          text = cells[i * num_columns + 3].text.strip()
          if not text or text == "Asset Name":
            return False
        return True
      except Exception:
        return False

    WebDriverWait(driver, 30).until(all_rows_ready)
    print("✅ Found the 'nis-async-grid' table and data has rendered.")

    cells = table.find_elements(By.TAG_NAME, "vaadin-grid-cell-content")

    rows = []
    for i in range(num_rows):
      start_index = i * num_columns
      row_data = [cell.text.strip() for cell in cells[start_index : start_index + num_columns - 1]]
      rows.append(row_data)

    return rows
  except Exception as e:
    print("❌ Table not found or an error occurred:", str(e))
    return []

def click_inspect_button(driver, row_index):
  from selenium.webdriver.common.action_chains import ActionChains
  try:
    time.sleep(2) # Give the grid time to stabilize
    buttons = WebDriverWait(driver, 10).until(
      EC.presence_of_all_elements_located((By.CLASS_NAME, "altfins-inspect-btn"))
    )
    
    visible_btns = []
    for b in buttons:
      try:
        if b.is_displayed():
          visible_btns.append(b)
      except Exception:
        pass
    
    # Sort top-to-bottom physically
    visible_btns.sort(key=lambda b: b.location.get('y', 0))
    
    if row_index < len(visible_btns):
      btn = visible_btns[row_index]
      
      # Scroll into view securely
      driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
      time.sleep(2)
      
      # Native click simulating user behavior avoids web component event dispatch issues
      try:
        ActionChains(driver).move_to_element(btn).click().perform()
      except Exception:
        try:
          btn.click()
        except Exception:
          driver.execute_script("arguments[0].click();", btn)
          
      print(f"✅ Click on the 'altfins-inspect-btn' in the row: {row_index + 1}.")
      time.sleep(5) # Wait for popup to render
    else:
      print(f"❌ Button not found in the row {row_index + 1}. Total visible: {len(visible_btns)}")
  except Exception as e:
    print("❌ Button not found or not clickable:", str(e))

def extract_popup_data(driver):
  try:
    # 1. Wait for the popup container to appear
    popup = WebDriverWait(driver, 15).until(
      EC.visibility_of_element_located((By.CLASS_NAME, "curated-chart-detail"))
    )
    
    # 2. STRICT WAIT: Poll until the popup text is long enough to be a real analysis
    # (a proper trade setup is always longer than 50 characters)
    WebDriverWait(driver, 15).until(
      lambda d: len(d.find_element(By.CLASS_NAME, "curated-chart-detail").text.strip()) > 50
    )
    
    popup_text = popup.text.strip()
    print("✅ Successfully retrieved data from the popup.")
    return popup_text
  except Exception as e:
    print("❌ Failed to retrieve data from the popup.")
    driver.save_screenshot(f"error_popup_data.png")
    return ""

def extract_popup_image(driver):
  try:
    img = WebDriverWait(driver, 15).until(
      EC.visibility_of_element_located((By.CLASS_NAME, "fullscreen-image"))
    )
    img_src = img.get_attribute("src")
    print("✅ Successfully retrieved the image.")
    return img_src
  except Exception as e:
    print("❌ Failed to retrieve the image from the popup.")
    return ""

def close_popup(driver):
  """Close the current popup by clicking outside or pressing Escape."""
  from selenium.webdriver.common.keys import Keys
  try:
    # Clicking the backdrop overlay is usually the most robust way to close Vaadin dialogs
    try:
      overlay = driver.find_element(By.TAG_NAME, "vaadin-dialog-overlay")
      driver.execute_script("arguments[0].click();", overlay)
    except Exception:
      driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)

    WebDriverWait(driver, 10).until(
      EC.invisibility_of_element_located((By.CLASS_NAME, "curated-chart-detail"))
    )
    print("✅ Popup closed.")
    time.sleep(3)  # Vital for Vaadin grids to finish re-rendering after overlay detach
  except Exception:
    pass

def main():
  driver = setup_driver()

  try:
    print("📌 ================= Start =================\n")
    login_with_email(driver, os.getenv("ALTFINS_ACCOUNT"), os.getenv("ALTFINS_PASSWORD"))

    load_website(driver, "https://altfins.com/technical-analysis")

    # Read ALL rows once — the grid is stable here (no popup open).
    # all_rows_ready() guarantees both rows are fully populated before we snapshot.
    num_rows = 2
    table_rows = extract_table_rows(driver, num_rows=num_rows)

    results = []

    for i, row_data in enumerate(table_rows):
      click_inspect_button(driver, i)

      popup_data = extract_popup_data(driver)
      popup_image = extract_popup_image(driver)

      results.append({
        "table_row": row_data,
        "popup_data": popup_data,
        "popup_image": popup_image
      })

      # Close popup before moving to next row
      close_popup(driver)
      time.sleep(2)

    save_data_to_supabase(results)

  finally:
    print("\n📌 ================= End =================")
    driver.quit()

if __name__ == "__main__":
  main()

