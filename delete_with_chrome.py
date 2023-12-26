import os
import sqlite3

import undetected_chromedriver as uc
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def new_driver(profile_path=None, headless=False):
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-first-run")

    driver = uc.Chrome(
        options=chrome_options,
        headless=headless,
        user_data_dir=profile_path,
        # browser_executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    )

    # delete_player_js = open('delete_player.js').read()
    # driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': delete_player_js})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["https://youtube.googleapis.com"]})
    driver.execute_cdp_cmd('Network.enable', {})
    return driver


def delete_if_taking_space(driver, url):
    driver.get(url)

    filename_el_xpath = "//*[contains(@aria-label, 'Filename: ')] | //*[contains(@aria-label, 'Имя файла: ')]"
    marker_xpath = "//*[contains(text(), 'Этот объект не занимает места')] | //*[contains(text(), 'take up space in your account storage')]"
    delete_button_xpath = "//*[@aria-label='Удалить'] | //*[@aria-label='Delete']"
    confirm_delete_button_xpath = "//*[contains(text(), 'Удалить')]/parent::button | //*[contains(text(), 'Move to trash')]/parent::button"
    file_deleted_xpath = "//*[contains(text(), 'перемещено в корзину.')] | //*[contains(text(), 'Moved to trash')]"
    wait = WebDriverWait(driver, 10)
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, filename_el_xpath)))
    except:
        print("info panel not found")
        open_info_xpath = "//*[@aria-label='Open info'] | //*[@aria-label='Показать дополнительные сведения']"
        info_button = driver.find_element(By.XPATH, open_info_xpath)
        info_button.click()
        wait.until(EC.element_to_be_clickable((By.XPATH, filename_el_xpath)))
        print("info panel opened")
    marker = None
    try:
        marker = driver.find_element(By.XPATH, marker_xpath)
    except NoSuchElementException:
        pass

    if marker and marker.text:
        print("no space taken")
        return False
    else:
        delete_button = driver.find_element(By.XPATH, delete_button_xpath)
        delete_button.click()
        confirm_delete_buttons = driver.find_elements(By.XPATH, confirm_delete_button_xpath)
        for confirm_delete_button in confirm_delete_buttons:
            if confirm_delete_button.text:
                confirm_delete_button.click()
                wait.until(EC.element_to_be_clickable((By.XPATH, file_deleted_xpath)))
                print("moved to trash")
                return True


def main():
    photos_db_path = "photos_db.sqlite"
    headless = True

    while True:
        profile_path = os.path.join(os.getcwd(), "driver_profile")
        first_run = not os.path.exists(profile_path)

        with sqlite3.connect(photos_db_path) as photos_db:
            photos_db_cursor = photos_db.cursor()
            photos_db_cursor.execute("SELECT productUrl, filename FROM uploaded_media WHERE isChecked IS NULL OR isDeleted IS NULL")
            items = photos_db_cursor.fetchall()

            if not items:
                print("Nothing to process")
                break

            if first_run:
                headless = False
                driver = new_driver(profile_path, headless=headless)
                input("Please log in to Google. Press Enter to continue, then restart the script")
                driver.quit()

            with new_driver(profile_path, headless=headless) as driver:
                for counter, item in enumerate(items):
                    product_url, filename_db = item
                    print(filename_db, f"{counter}/{len(items)}")

                    if delete_if_taking_space(driver, product_url):
                        sqlite_query = "UPDATE uploaded_media SET isDeleted = ? WHERE productUrl = ?"
                    else:
                        sqlite_query = "UPDATE uploaded_media SET isChecked = ? WHERE productUrl = ?"

                    parameters = (1, product_url)
                    photos_db_cursor.execute(sqlite_query, parameters)
                    photos_db.commit()


if __name__ == "__main__":
    main()
