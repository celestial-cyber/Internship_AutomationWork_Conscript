from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, json

driver = webdriver.Chrome()
driver.get("https://isha.sadhguru.org/in/en/yoga-meditation/yoga-program-for-beginners/hatha-yoga/courses-by-certified-teachers")
time.sleep(5)

clicks = 0
while True:
    try:
        btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Load More')] | //a[contains(text(),'Load More')]"))
        )
        driver.execute_script("arguments[0].click();", btn)
        clicks += 1
        print(f"Click #{clicks}")
        time.sleep(3)
    except:
        print(f"Done after {clicks} clicks")
        break

# Extract teachers
cards = driver.find_elements(By.CSS_SELECTOR, "[class*='teacher'], [class*='card']")
teachers = []
for i, card in enumerate(cards):
    teachers.append({
        "index": i+1,
        "text": card.text
    })

# Save to file
with open("Isha_Certified_Yoga_Trainers.txt", "w", encoding="utf-8") as f:
    f.write(f"Total: {len(teachers)}\nClicks: {clicks}\n\n")
    for t in teachers:
        f.write(f"[{t['index']}]\n{t['text']}\n\n{'='*50}\n")

driver.quit()
print(f"Saved {len(teachers)} teachers")
