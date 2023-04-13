from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import pandas as pd
import schedule
import time
from datetime import datetime
import os

def get():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    bro = webdriver.Chrome(options=options)
    
    try:
        bro.get('https://report.amap.com/ajax/getCityRank.do')
        page_text = bro.page_source
        bro.quit()
        text = page_text[25:-14]
        data = json.loads(text)
        df = pd.DataFrame(data)
    except:
        return
    
    log_path = './log/' + datetime.now().strftime('%m-%d')
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    file_name = datetime.now().strftime('%H-%M')
    file_path = log_path + f'/{file_name}.csv'
    df.to_csv(file_path, index=False)
    
def morning():
    schedule.every(10).minutes.until('22:00').do(get)
    date = datetime.now().strftime('%m-%d')
    print(f'{date}, morning!')
    

if __name__ == '__main__':
    schedule.every().day.at('05:50').do(morning)
    while True:
        schedule.run_pending()
        time.sleep(1)
