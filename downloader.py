import os
import re
from urllib import request

import plac
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm


class StudMedLibDownloader:
    def __init__(self, login, password, book_url, driver_path="./driver/chromedriver"):
        self.login = login
        self.password = password
        self.book_url = book_url
        self.chapters = []
        self.download_dir = './images'

        # TODO: Check download_dir

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # TODO: Check driver_path

        self.driver = webdriver.Chrome(options=options,
                                       executable_path=(driver_path))

        self.wait = WebDriverWait(self.driver, 10)

    def log_in(self):
        print('Logining...')
        studmedlib_login = "http://www.studmedlib.ru/ru/cur_user/entry.html"
        self.driver.get(studmedlib_login)

        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="new_UName"]')
        )).send_keys(self.login)

        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="new_PWord"]')
        )).send_keys(self.password)

        self.wait.until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="try_UNamePWord"]')
        )).click()

        return self

    def load_book_page(self):
        print('Loading book page...')
        self.driver.get(self.book_url)
        return self

    def get_chapters(self):
        print('Getting chapters...')
        page_source_overview = self.driver.page_source
        soup = BeautifulSoup(page_source_overview, 'lxml')

        self.chapters = soup.select("#table_of_contents > "
                                    "div.table-of-contents > "
                                    "div > div > a:first-child")

        return self

    def download_book(self):
        def get_total_pages_number():
            print('Getting total page number...')
            total_num = 0
            for chapter in tqdm(self.chapters):
                self.driver.get(chapter['href'])
                total_num += int(self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.wrap-pages-reader > span:nth-child(3)')
                )).text)
            return total_num

        def go_to_chapter(chapter):
            self.driver.get(chapter['href'])

        def switch_to_book_mode():
            self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.wrap-book-mode')
            )).click()

        def donwload_page(page):

            style = page.get_attribute('style')
            url = re.search(r'url\("(http.+\.jpg)"\)', style).group(1)

            pages_count = len([page for page in sorted(os.listdir(self.download_dir)) if page.endswith('.jpg')]) + 1
            page_name = f"{'0' * (5 - len(str(pages_count)))}{pages_count}.jpg"

            request.urlretrieve(url, f'{self.download_dir}/{page_name}')

        def go_to_next_page():
            next_page_btn = self.driver.find_element_by_css_selector('div.arrow-right-tab > a')
            next_page_btn.click()

        total = get_total_pages_number()
        print('Downloading pages...')

        pbar = tqdm(total=total)

        for chapter in self.chapters:
            go_to_chapter(chapter)
            switch_to_book_mode()

            chapter_pages = int(self.wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.wrap-pages-reader > span:nth-child(3)')
            )).text)

            while True:
                try:
                    page = self.wait.until(EC.presence_of_element_located(
                        (By.XPATH, '//*[@id="cur_page_content"]/img')
                    ))
                    donwload_page(page)
                except Exception:
                    self.driver.refresh()
                    continue

                current_page = int(self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.wrap-pages-reader > span.cur-num')
                )).text)

                pbar.update(1)
                if current_page == chapter_pages:
                    break

                go_to_next_page()

        pbar.close()

        self.driver.quit()


@plac.pos('login', "Login to studmedlib", type=str)
@plac.pos('password', "Password to studmedlib", type=str)
@plac.pos('book_url', "Book url", type=str)
def main(login, password, book_url):
    downloader = StudMedLibDownloader(login, password, book_url)
    downloader.log_in()
    downloader.load_book_page().get_chapters().download_book()


if __name__ == '__main__':
    plac.call(main)
