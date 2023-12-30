import os

import undetected_chromedriver as uc

driver_data_path = os.path.join(os.getcwd(), "driver_data")

driver = uc.Chrome(headless=False, user_data_dir=driver_data_path)

input("Please log into Google. Google Photos media info panel must be opened. Press Enter to continue")
driver.quit()
