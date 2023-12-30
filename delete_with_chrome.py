import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from rich.progress import (BarColumn, MofNCompleteColumn, Progress,
                           ProgressColumn, SpinnerColumn, Task,
                           TimeElapsedColumn, TimeRemainingColumn)
from rich.text import Text
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire import undetected_chromedriver as uc


def new_driver(driver_data_path=None, headless=False):
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-features=InterestFeedContentSuggestions")
    chrome_options.add_argument('--disable-features=Translate')
    chrome_options.page_load_strategy = 'eager'

    driver = uc.Chrome(
        options=chrome_options,
        headless=headless,
        user_data_dir=driver_data_path,
        # browser_executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    )

    driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["https://youtube.googleapis.com"]})
    driver.execute_cdp_cmd('Network.enable', {})

    def interceptor(request):
        accept = request.headers.get('Accept')
        if accept == "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8":
            request.abort()

    driver.request_interceptor = interceptor
    return driver


def does_not_exist_check(wait):
    does_not_exist_xpath = "//h1[contains(text(), 'Не удается получить доступ')] | //h1[contains(text(), 'access photo')]"
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, does_not_exist_xpath)))
        return True
    except:
        return None


def is_panel_closed(driver):
    """Unused"""
    panel_xpath = "/html/body/div[1]/div/c-wiz/div[4]/c-wiz/div[1]/div[4]"
    try:
        panel = driver.find_element(By.XPATH, panel_xpath)
        if panel and not panel.text:
            return True
    except:
        return None


def open_info_panel(driver, filename_el_xpath):
    """Unused"""
    open_info_xpath = "//*[@aria-label='Open info'] | //*[@aria-label='Показать дополнительные сведения']"
    try:
        info_button = driver.find_element(By.XPATH, open_info_xpath)
        info_button.click()
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, filename_el_xpath)))
        return True
    except:
        return None


def uses_no_space_check(wait):
    space_marker_xpath = "//*[contains(text(), 'Этот объект не занимает места')] | //*[contains(text(), 'take up space in your account storage')]"
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, space_marker_xpath)))
        return True
    except:
        return None


def uses_space_check(wait):
    takes_space_xpath = "//*[contains(@aria-label, 'File size: ')] | //*[contains(@aria-label, 'Размер файла: ')]"
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, takes_space_xpath)))
        return True
    except:
        return None


def delete_media(driver):
    wait = WebDriverWait(driver, 5)
    delete_button_xpath = "//*[@aria-label='Удалить'] | //*[@aria-label='Delete']"
    confirm_delete_button_xpath = "//*[contains(text(), 'Удалить')]/parent::button | //*[contains(text(), 'Move to trash')]/parent::button"
    file_deleted_xpath = "//*[contains(text(), 'перемещено в корзину.')] | //*[contains(text(), 'Moved to trash')]"
    try:
        delete_button = driver.find_element(By.XPATH, delete_button_xpath)
        delete_button.click()
        confirm_delete_buttons = driver.find_elements(By.XPATH, confirm_delete_button_xpath)
        for confirm_delete_button in confirm_delete_buttons:
            if confirm_delete_button.text:
                confirm_delete_button.click()
                wait.until(EC.element_to_be_clickable((By.XPATH, file_deleted_xpath)))
                print("moved to trash")
                return True
    except:
        return False


def check_current_media_name(driver, filename_el_xpath, filename_db):
    """Check if current media is the one we need"""
    try:
        filename_web = driver.find_element(By.XPATH, filename_el_xpath)
        if filename_web and filename_web.text == filename_db:
            return True
    except:
        return False


def delete_if_taking_space(driver, url, filename_db):
    filename_el_xpath = "//*[contains(@aria-label, 'Filename: ')] | //*[contains(@aria-label, 'Имя файла: ')]"
    if not check_current_media_name(driver, filename_el_xpath, filename_db):
        driver.get(url)

    wait = WebDriverWait(driver, 0.05)

    while True:
        if does_not_exist_check(wait):
            print("does_not_exist")
            return True
        # elif is_panel_closed(driver):
        #     if open_info_panel(driver, filename_el_xpath):
        #         continue
        elif uses_no_space_check(wait):
            print("no space taken")
            return False
        elif uses_space_check(wait):
            if delete_media(driver):
                return True


class IterationsPerSecondColumn(ProgressColumn):
    """A column that shows the number of iterations per second."""

    def render(self, task: "Task") -> Text:
        """Show the number of iterations per second."""
        it_per_second = task.speed
        if it_per_second is None:
            return Text("0.0 it/s", style="progress.percentage")
        else:
            return Text(f"{it_per_second:.2f} it/s", style="progress.percentage")


def main():
    photos_db_path = "photos_db.sqlite"
    headless = False
    driver_data_path = os.path.join(os.getcwd(), "driver_data")

    while True:
        try:
            with sqlite3.connect(photos_db_path) as photos_db:
                photos_db_cursor = photos_db.cursor()
                photos_db_cursor.execute("SELECT productUrl, filename FROM uploaded_media WHERE isChecked IS NULL AND isDeleted IS NULL")
                items = photos_db_cursor.fetchall()

                if not items:
                    print("Nothing to process")
                    break
            driver = new_driver(driver_data_path, headless=headless)

            with Progress(
                SpinnerColumn(),
                "[progress.description]{task.description}",
                BarColumn(),
                IterationsPerSecondColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                MofNCompleteColumn()
            ) as progress:
                task = progress.add_task("[cyan]Processing...", total=len(items))
                for product_url, filename_db in items:
                    print(filename_db)
                    executor = ThreadPoolExecutor(max_workers=1)
                    future = executor.submit(delete_if_taking_space, driver, product_url, filename_db)
                    try:
                        success = future.result(timeout=30)
                    except TimeoutError:
                        future.cancel()
                        raise Exception('delete_if_taking_space timeout')
                    if success:
                        if success == True:
                            sqlite_query = "UPDATE uploaded_media SET isDeleted = ? WHERE productUrl = ?"
                        elif success == False:
                            sqlite_query = "UPDATE uploaded_media SET isChecked = ? WHERE productUrl = ?"
                        elif success == None:
                            raise Exception("check error!")

                        parameters = (1, product_url)
                        photos_db_cursor.execute(sqlite_query, parameters)
                        photos_db.commit()
                        progress.update(task, advance=1)
        except Exception as e:
            print(e)
        finally:
            driver.quit() if driver else None


if __name__ == "__main__":
    main()
