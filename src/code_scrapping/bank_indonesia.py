import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import re
from bs4 import BeautifulSoup


def setup_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    print("Browser berhasil diinisialisasi")
    return driver

def change_format_date(teks):
    if not teks or teks == 'N/A':
        return None
    bulan = {
        'januari': '01', 'februari': '02', 'maret': '03', 'april': '04',
        'mei': '05', 'juni': '06', 'juli': '07', 'agustus': '08',
        'september': '09', 'oktober': '10', 'november': '11', 'desember': '12'
    }
    match = re.search(r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', teks)
    if match:
        day = match.group(1).zfill(2)
        month = bulan.get(match.group(2).lower(), '01')
        year = match.group(3)
        return f"{year}-{month}-{day}"
    return None


def search_news(driver, keyword):
    try:
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "TextBoxSearch"))
        )
        search_box.clear()
        search_box.send_keys(keyword)
        print(f"Keyword '{keyword}' berhasil diinput")
        try:
            filter_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-outline-primary.btn--filter"))
            )
            filter_button.click()
            time.sleep(2)
        except:
            pass
        try:
            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ctl54_g_895e8ef2_eaad_4a83_9db7_1632dd8595c0_ctl00_ButtonFilter"))
            )
            submit_button.click()
        except:
            search_box.send_keys(Keys.RETURN)
        print(f"Menunggu hasil pencarian...")
        time.sleep(60)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".media.media--pers"))
        )
        time.sleep(3)
        print(f"Hasil pencarian berhasil di-load")
    except Exception as e:
        print(f"Error saat search: {e}")

def get_article_content(driver, url):
    try:
        print(f"\nMengambil konten dari: {url}")
        driver.get(url)
        time.sleep(5)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ms-rtestate-field"))
        )
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        content_div = soup.find('div', id='ctl00_PlaceHolderMain_ctl05__ControlWrapper_RichHtmlField')
        if not content_div:
            print("✗ Konten div tidak ditemukan")
            return "N/A"
        paragraphs = content_div.find_all('p')
        print(f"Ditemukan {len(paragraphs)} paragraf")
        content_text = []
        for idx, p in enumerate(paragraphs, 1):
            text = p.get_text(strip=True)
            if not text or len(text) < 5:
                continue
            if "Jakarta," in text and "Departemen Komunikasi" in text:
                print(f"  Paragraph #{idx}: SKIPPED (footer)")
                continue
            if text.startswith("No. ") and "DKom" in text:
                print(f"  Paragraph #{idx}: SKIPPED (nomor surat)")
                continue
            if len(text) >= 30:
                content_text.append(text)
                print(f"  Paragraph #{idx}: ADDED ({len(text)} chars)")
            else:
                print(f"  Paragraph #{idx}: SKIPPED (too short: {len(text)} chars)")
        if content_text:
            result = "\n\n".join(content_text).strip()
            print(f"\nTotal konten: {len(result)} characters")
            return result
        else:
            print("✗ Tidak ada konten yang bisa diambil")
            return "N/A"
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return "N/A"
    
def scrape_current_page_with_date_filter(driver, target_date):
    news_data = []
    should_stop = False
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".media-list"))
        )
        news_items = driver.find_elements(By.CSS_SELECTOR, ".media.media--pers")
        print(f"   Ditemukan {len(news_items)} berita di halaman ini")
        target_datetime = datetime.strptime(target_date, "%Y-%m-%d")
        for idx, item in enumerate(news_items, 1):
            try:
                try:
                    title_element = item.find_element(By.CSS_SELECTOR, ".media__title")
                    title = title_element.text.strip()
                    url = title_element.get_attribute("href")
                except:
                    continue
                try:
                    subtitle = item.find_element(By.CSS_SELECTOR, ".media__subtitle").text.strip()
                    parts = subtitle.split("•")
                    date_str = parts[0].strip() if len(parts) > 0 else None
                except:
                    continue
                formatted_date = change_format_date(date_str)
                if not formatted_date:
                    print(f"Gagal parse tanggal: {date_str}")
                    continue
                article_datetime = datetime.strptime(formatted_date, "%Y-%m-%d")
                if article_datetime < target_datetime:
                    print(f"Ditemukan artikel lebih lama ({formatted_date}) di posisi #{idx}, STOP scraping")
                    should_stop = True
                    break
                if formatted_date == target_date:
                    print(f"Match: {title[:60]}... ({formatted_date})")
                    news_data.append({
                        "title": title,
                        "date": formatted_date,
                        "url": url,
                        "content": None
                    })
                else:
                    print(f"Skip: {title[:60]}... ({formatted_date})")
            except Exception as e:
                print(f"Error parsing berita #{idx}: {e}")
                continue
    except TimeoutException:
        print("Timeout menunggu elemen berita")
    except Exception as e:
        print(f"Error saat scraping: {e}")
    return news_data, should_stop


def go_to_next_page(driver):
    try:
        next_button = driver.find_element(By.CSS_SELECTOR, "input.next[type='image']")
        
        is_disabled = next_button.get_attribute("disabled")
        if is_disabled:
            print("Sudah mencapai halaman terakhir")
            return False
        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
        time.sleep(1)
        next_button.click()
        print("Pindah ke halaman berikutnya...")
        time.sleep(3)
        return True
    except:
        return False

def scrape_bi_with_date(url, keyword, target_date, headless=True):
    all_news = []
    page_count = 1
    driver = None
    try:
        driver = setup_driver(headless=headless)
        print(f"\nMengakses: {url}")
        print(f"Keyword: '{keyword}'")
        print(f"Target tanggal: {target_date}")
        print("="*80)
        driver.get(url)
        time.sleep(3)
        if keyword:
            search_news(driver, keyword)
        should_stop = False
        while not should_stop:
            print(f"\nScraping Halaman {page_count}...")
            news_data, should_stop = scrape_current_page_with_date_filter(driver, target_date)
            all_news.extend(news_data)
            print(f"Berita yang cocok di halaman ini: {len(news_data)}")
            print(f"Total berita terkumpul: {len(all_news)}")
            if should_stop:
                print(f"\nBerhenti scraping karena menemukan artikel lebih lama dari {target_date}")
                break
            if not go_to_next_page(driver):
                break
            page_count += 1
        print(f"\n" + "="*80)
        print(f"Scraping list selesai! Ditemukan {len(all_news)} berita pada tanggal {target_date}")
        if all_news:
            print(f"\nMulai mengambil konten lengkap untuk {len(all_news)} berita...")
            print("="*80)
            for i, news in enumerate(all_news, 1):
                print(f"\n({i}/{len(all_news)}) {news['title'][:60]}...")
                news['content'] = get_article_content(driver, news['url'])
                time.sleep(2)
        print(f"\n" + "="*80)
        print(f"Selesai! Total {len(all_news)} berita dengan konten lengkap")
    except Exception as e:
        print(f"\nError saat scraping: {e}")
    finally:
        if driver:
            driver.quit()
            print("Browser ditutup")
    return all_news

def main_bank_indonesia(keyword, tanggal):
    url = "https://www.bi.go.id/id/publikasi/ruang-media/news-release/Default.aspx"
    news_data = scrape_bi_with_date(
        url=url,
        keyword=keyword,
        target_date=tanggal,
        headless=True
    )
    if news_data:
        df = pd.DataFrame(news_data)
        print(f"\nDitemukan {len(df)} berita")
        print("\nPreview data berita:")
        print(df[['title', 'date', 'url']].head())
        safe_keyword = "".join(c for c in keyword if c.isalnum() or c in (' ', '_')).rstrip()
        safe_keyword = safe_keyword.replace(' ', '_')
        return df
    else:
        print(f"\nTidak ada berita ditemukan untuk keyword '{keyword}' pada tanggal {tanggal}")
        return None
    
if __name__ == "__main__":
    result = main_bank_indonesia(
        keyword="BI Rate",
        target_date="2025-08-29"
    )
    if result is not None:
        print(f"\nTotal berita: {len(result)}")
        print(f"Kolom: {', '.join(result.columns)}")