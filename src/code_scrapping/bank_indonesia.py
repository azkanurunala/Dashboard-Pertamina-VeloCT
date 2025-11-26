import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime


class BankIndonesiaScraper:
    def __init__(self, headless=True):
        """
        Inisialisasi scraper
        
        Args:
            headless (bool): Jalankan browser tanpa GUI (default: True)
        """
        self.url = "https://www.bi.go.id/id/publikasi/ruang-media/news-release/Default.aspx"
        self.driver = None
        self.headless = headless
        
    def setup_driver(self):
        """Setup Selenium WebDriver dengan Chrome"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        print("✓ Browser berhasil diinisialisasi")
        
    def search_news(self, keyword):
        """
        Melakukan pencarian berita
        
        Args:
            keyword (str): Kata kunci pencarian
        """
        try:
            # Cari input search box
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input[name='search'], #searchBox"))
            )
            
            # Clear dan input keyword
            search_box.clear()
            search_box.send_keys(keyword)
            
            # Cari tombol search
            search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .search-button, .btn-search")
            search_button.click()
            
            print(f"✓ Pencarian untuk '{keyword}' berhasil dijalankan")
            time.sleep(3)  # Tunggu hasil load
            
        except Exception as e:
            print(f"⚠ Search box tidak ditemukan atau error: {e}")
            print("Melanjutkan scraping tanpa filter pencarian...")
    
    def scrape_current_page(self):
        """
        Scrape data dari halaman yang sedang aktif
        
        Returns:
            list: List of dictionaries berisi data berita
        """
        news_data = []
        
        try:
            # Tunggu elemen berita muncul
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".media-list, .news-list, .list-news"))
            )
            
            # Cari semua item berita
            # Sesuaikan selector berdasarkan struktur HTML BI
            news_items = self.driver.find_elements(By.CSS_SELECTOR, ".media.media--pers, .news-item, article")
            
            print(f"   Ditemukan {len(news_items)} berita di halaman ini")
            
            for idx, item in enumerate(news_items, 1):
                try:
                    # Ambil nomor siaran pers
                    try:
                        number = item.find_element(By.CSS_SELECTOR, ".media__number, .news-number").text.strip()
                    except:
                        number = f"N/A"
                    
                    # Ambil judul
                    try:
                        title_element = item.find_element(By.CSS_SELECTOR, ".media__title, .news-title, h3 a, h2 a")
                        title = title_element.text.strip()
                        link = title_element.get_attribute("href")
                    except:
                        title = "N/A"
                        link = "N/A"
                    
                    # Ambil tanggal
                    try:
                        date = item.find_element(By.CSS_SELECTOR, ".media__date, .news-date, .date").text.strip()
                    except:
                        date = "N/A"
                    
                    # Ambil snippet/deskripsi jika ada
                    try:
                        snippet = item.find_element(By.CSS_SELECTOR, ".media__description, .news-desc, p").text.strip()
                    except:
                        snippet = ""
                    
                    news_data.append({
                        "nomor": number,
                        "judul": title,
                        "tanggal": date,
                        "snippet": snippet,
                        "link": link
                    })
                    
                except Exception as e:
                    print(f"   ⚠ Error parsing berita #{idx}: {e}")
                    continue
            
        except TimeoutException:
            print("   ⚠ Timeout menunggu elemen berita")
        except Exception as e:
            print(f"   ⚠ Error saat scraping halaman: {e}")
        
        return news_data
    
    def go_to_next_page(self):
        """
        Pindah ke halaman berikutnya
        
        Returns:
            bool: True jika berhasil, False jika sudah halaman terakhir
        """
        try:
            # Coba cari tombol next dengan berbagai selector
            next_selectors = [
                "a.next",
                "a[aria-label='Next']",
                ".pagination-next",
                "li.next a",
                ".ms-promlink-button-next",
                "a:contains('Next')",
                "a:contains('›')",
                "a:contains('»')"
            ]
            
            next_button = None
            for selector in next_selectors:
                try:
                    if "contains" in selector:
                        # Untuk XPath contains
                        next_button = self.driver.find_element(By.XPATH, f"//a[contains(text(), 'Next') or contains(text(), '›') or contains(text(), '»')]")
                    else:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if next_button:
                        break
                except:
                    continue
            
            if not next_button:
                print("   ℹ Tombol 'Next' tidak ditemukan (mungkin sudah halaman terakhir)")
                return False
            
            # Check apakah tombol disabled
            classes = next_button.get_attribute("class") or ""
            if "disabled" in classes or "inactive" in classes:
                print("   ℹ Sudah mencapai halaman terakhir")
                return False
            
            # Scroll ke tombol dan klik
            self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            time.sleep(1)
            next_button.click()
            
            print("   ✓ Pindah ke halaman berikutnya...")
            time.sleep(3)  # Tunggu halaman load
            
            return True
            
        except Exception as e:
            print(f"   ⚠ Tidak bisa pindah ke halaman berikutnya: {e}")
            return False
    
    def scrape_all_pages(self, max_pages=None, search_keyword=None):
        """
        Scrape semua halaman berita
        
        Args:
            max_pages (int): Maksimal halaman yang di-scrape (None = semua)
            search_keyword (str): Kata kunci untuk filter berita
            
        Returns:
            list: List of dictionaries berisi semua data berita
        """
        all_news = []
        page_count = 1
        
        try:
            self.setup_driver()
            print(f"\n📰 Mengakses: {self.url}")
            self.driver.get(self.url)
            time.sleep(3)
            
            # Lakukan search jika ada keyword
            if search_keyword:
                print(f"\n🔍 Mencari berita dengan keyword: '{search_keyword}'")
                self.search_news(search_keyword)
            
            # Loop scraping per halaman
            while True:
                print(f"\n📄 Scraping Halaman {page_count}...")
                
                # Scrape halaman saat ini
                news_data = self.scrape_current_page()
                all_news.extend(news_data)
                
                print(f"   ✓ Berhasil scrape {len(news_data)} berita")
                print(f"   📊 Total berita terkumpul: {len(all_news)}")
                
                # Check apakah sudah mencapai max_pages
                if max_pages and page_count >= max_pages:
                    print(f"\n✓ Mencapai batas maksimal {max_pages} halaman")
                    break
                
                # Coba pindah ke halaman berikutnya
                if not self.go_to_next_page():
                    break
                
                page_count += 1
            
            print(f"\n✅ Scraping selesai! Total {len(all_news)} berita dari {page_count} halaman")
            
        except Exception as e:
            print(f"\n❌ Error saat scraping: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
                print("✓ Browser ditutup")
        
        return all_news
    
    def save_to_csv(self, data, filename=None):
        """
        Simpan data ke file CSV
        
        Args:
            data (list): Data berita
            filename (str): Nama file output
        """
        if not data:
            print("⚠ Tidak ada data untuk disimpan")
            return
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bi_news_{timestamp}.csv"
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n💾 Data berhasil disimpan ke: {filename}")
        print(f"   Total baris: {len(df)}")


def main():
    """Fungsi utama untuk menjalankan scraper"""
    
    print("="*60)
    print("  SCRAPER BERITA BANK INDONESIA")
    print("="*60)
    
    # Konfigurasi scraping
    scraper = BankIndonesiaScraper(headless=True)  # Set False untuk melihat browser
    
    # Pilihan: 
    # 1. Scrape tanpa search, maksimal 3 halaman
    # news_data = scraper.scrape_all_pages(max_pages=3)
    
    # 2. Scrape dengan search keyword
    # news_data = scraper.scrape_all_pages(max_pages=5, search_keyword="inflasi")
    
    # 3. Scrape semua halaman (hati-hati, bisa lama!)
    news_data = scraper.scrape_all_pages(max_pages=2)
    
    # Simpan ke CSV
    if news_data:
        scraper.save_to_csv(news_data)
        
        # Preview data
        print("\n📋 Preview 3 berita pertama:")
        print("-" * 60)
        for i, news in enumerate(news_data[:3], 1):
            print(f"\n{i}. {news['nomor']}")
            print(f"   Judul: {news['judul'][:80]}...")
            print(f"   Tanggal: {news['tanggal']}")
    else:
        print("\n⚠ Tidak ada data yang berhasil di-scrape")


if __name__ == "__main__":
    main()