from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import time
import traceback
import sys 
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from helpers.scraping_helper import setup_driver

def clean_date_cnbc(raw_date: str) -> str:
    now = datetime.now()
    raw_date_original = raw_date
    raw_date = raw_date.strip().lower()
    if match_tahun := re.search(r"(\d+)\s*tahun", raw_date):
        years_ago = int(match_tahun.group(1))
        target_date = now - timedelta(days=years_ago * 365)
        result = target_date.strftime("%d %b %Y")
        print(f"'{raw_date_original}' → '{result}' ({years_ago} tahun lalu)")
        return result
    if match_bulan := re.search(r"(\d+)\s*bulan", raw_date):
        months_ago = int(match_bulan.group(1))
        target_date = now - timedelta(days=months_ago * 30)
        result = target_date.strftime("%d %b %Y")
        print(f"'{raw_date_original}' → '{result}' ({months_ago} bulan lalu)")
        return result
    if match_minggu := re.search(r"(\d+)\s*minggu", raw_date):
        weeks_ago = int(match_minggu.group(1))
        target_date = now - timedelta(weeks=weeks_ago)
        result = target_date.strftime("%d %b %Y")
        print(f"'{raw_date_original}' → '{result}' ({weeks_ago} minggu lalu)")
        return result
    if match_hari := re.search(r"(\d+)\s*hari", raw_date):
        days_ago = int(match_hari.group(1))
        target_date = now - timedelta(days=days_ago)
        result = target_date.strftime("%d %b %Y")
        print(f"'{raw_date_original}' → '{result}' ({days_ago} hari lalu)")
        return result
    if "yang lalu" in raw_date:
        match_jam = re.search(r"(\d+)\s*jam", raw_date)
        hours_ago = int(match_jam.group(1)) if match_jam else 0
        match_menit = re.search(r"(\d+)\s*menit", raw_date)
        minutes_ago = int(match_menit.group(1)) if match_menit else 0
        delta = timedelta(hours=hours_ago, minutes=minutes_ago)
        target_datetime = now - delta
        result = target_datetime.strftime("%d %b %Y")
        print(f"'{raw_date_original}' → '{result}' ({hours_ago}h {minutes_ago}m yang lalu)")
        return result
    bulan_id_to_en = {
        'januari': 'Jan', 'februari': 'Feb', 'maret': 'Mar', 'april': 'Apr',
        'mei': 'May', 'juni': 'Jun', 'juli': 'Jul', 'agustus': 'Aug',
        'september': 'Sep', 'oktober': 'Oct', 'november': 'Nov', 'desember': 'Dec'
    }
    for id_month, en_month in bulan_id_to_en.items():
        if id_month in raw_date:
            raw_date = raw_date.replace(id_month, en_month)
            break
    if match_tanggal := re.match(r"(\d{1,2}\s+\w+\s+\d{4})", raw_date):
        result = match_tanggal.group(1).strip()
        print(f" [DATE] '{raw_date_original}' → '{result}' (format absolut)")
        return result
    return raw_date

def find_pagination_container_by_pattern(soup, min_links=3): 
    all_divs = soup.find_all("div")
    candidates = []
    for div in all_divs:
        links = div.find_all("a", href=True)
        link_count = len(links)
        if link_count >= min_links:
            numbers_in_links = []
            for a in links:
                text = a.get_text(strip=True)
                if text.isdigit():
                    numbers_in_links.append(int(text))
            has_valid_pagination = False
            if 1 in numbers_in_links and len(numbers_in_links) >= 2:
                numbers_in_links_sorted = sorted(numbers_in_links)
                if numbers_in_links_sorted[0] == 1:
                    consecutive_count = 1
                    for i in range(len(numbers_in_links_sorted) - 1):
                        if numbers_in_links_sorted[i+1] - numbers_in_links_sorted[i] == 1:
                            consecutive_count += 1
                        else:
                            break
                    if consecutive_count >= 2:
                        has_valid_pagination = True
            has_page_param = any(re.search(r"[?&]page=\d+", a.get("href", "")) for a in links)
            if has_valid_pagination and has_page_param:
                candidates.append({
                    'element': div,
                    'link_count': link_count,
                    'classes': div.get('class', []),
                    'numbers': numbers_in_links,
                    'has_valid_pagination': has_valid_pagination,
                    'has_page_param': has_page_param
                })
                print(f"Candidate: {link_count} links, angka={sorted(numbers_in_links)}, "
                      f"classes={div.get('class', [])[:3]}")
    if not candidates:
        print("Tidak ada container yang cocok dengan pola")
        return None
    best = max(candidates, key=lambda x: len(x['numbers']))
    same_number_count = [c for c in candidates if len(c['numbers']) == len(best['numbers'])]
    if len(same_number_count) > 1:
        best = min(same_number_count, key=lambda x: x['link_count'])
    return best['element']

def get_total_pages_from_pagination(pagination_element) -> int:
    if not pagination_element:
        return 1
    page_links = pagination_element.find_all("a", href=True)
    max_page = 1
    for a in page_links:
        href = a.get("href", "")
        match_href = re.search(r"[?&]page=(\d+)", href)
        if match_href:
            page_num = int(match_href.group(1))
            if page_num > max_page:
                max_page = page_num
        text = a.get_text(strip=True)
        if text.isdigit():
            page_num = int(text)
            if page_num > max_page:
                max_page = page_num
                print(f"  → Page {page_num} dari text: '{text}'")
    print(f"\nTotal: {max_page} halaman")
    return max_page

def find_article_container_by_pattern(soup):
    all_divs = soup.find_all("div")
    candidates = []
    for div in all_divs:
        sections = div.find_all("section", recursive=False)
        articles = div.find_all("article", recursive=False)
        total_items = len(sections) + len(articles)
        if total_items >= 3: 
            div_classes = div.get('class', [])
            class_str = " ".join(div_classes).lower()
            has_list_indicator = any(keyword in class_str for keyword in ['list', 'grid', 'container', 'content'])
            links = div.find_all("a", href=True)
            candidates.append({
                'element': div,
                'sections': len(sections),
                'articles': len(articles),
                'total_items': total_items,
                'links': len(links),
                'classes': div_classes,
                'has_list_indicator': has_list_indicator
            })
    if not candidates:
        print("Tidak ada container, fallback ke semua <section>")
        return None
    best = max(candidates, key=lambda x: (x['total_items'], x['has_list_indicator'], x['links']))
    print(f"Container terpilih: {best['total_items']} items, classes={best['classes']}")
    return best['element']

def parse_article_section(section):
    try:
        link_tag = section.find("a", class_="group", href=True)
        if not link_tag:
            link_tag = section.find("a", href=True)
        if not link_tag:
            return None
        link = link_tag.get("href", "")
        if not link.startswith("http"):
            if link.startswith("/"):
                link = "https://www.cnbcindonesia.com" + link
        title_tag = link_tag.find("strong")
        if not title_tag:
            title_tag = link_tag.find("h2")
        if not title_tag:
            title_tag = link_tag.find("h3")
        if not title_tag:
            title_tag = link_tag
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        date_tag = link_tag.find("span", class_="text-xs text-gray")
        if not date_tag:
            date_tag = link_tag.find("span", class_=lambda x: x and "text-xs" in " ".join(x))
        if not date_tag:
            date_tag = link_tag.find("time")
        raw_date = date_tag.get_text(strip=True) if date_tag else ""
        pub_date = clean_date_cnbc(raw_date) if raw_date else ""
        return {
            "title": title,
            "date": pub_date,
            "link": link,
        }
    except Exception as e:
        return None

def parse_cnbc_page_with_selenium(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "section"))
        )
        time.sleep(2)
    except Exception as e:
        print(f"Timeout: {e}")
        return [], None
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    container = find_article_container_by_pattern(soup)
    if container:
        sections = container.find_all("section")
        if not sections:
            sections = container.find_all("article")
    else:
        sections = soup.find_all("section")    
    page_results = []
    for idx, section in enumerate(sections, 1):
        article_data = parse_article_section(section)
        if article_data:
            print(f"  [{idx}] {article_data['title'][:60]}...")
            page_results.append(article_data)
        else:
            print(f"  [{idx}] Gagal parse")
    print(f"Berhasil parse: {len(page_results)} artikel")
    return page_results, soup

def clean_content_text(text: str) -> str:
    prefixes = [
        "Jakarta, CNBC Indonesia - ",
        "Jakarta, CNBC Indonesia-",
        "Jakarta, CNBC Indonesia –",
        "Jakarta, CNBC Indonesia– "
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    if text.startswith("(") and text.endswith(")") and len(text) < 30:
        return ""
    if text.startswith("(") and text.endswith(")"):
        return ""
    return text.strip()

def find_content_container_by_pattern(soup):
    all_divs = soup.find_all("div")
    candidates = []
    for div in all_divs:
        all_paragraphs = div.find_all("p")
        if len(all_paragraphs) < 3:
            continue
        candidates.append({
            'element': div,
            'paragraphs': len(all_paragraphs),
            'classes': div.get('class', [])
        })
    if not candidates:
        return None
    best = max(candidates, key=lambda x: x['paragraphs'])
    return best['element']

def scrape_cnbc_article_content_selenium(driver, url: str) -> str:
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "p"))
            )
        except:
            print(f"Timeout menunggu konten")
            return ""
        time.sleep(2)
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        content_div = find_content_container_by_pattern(soup)
        if not content_div:
            content_div = soup.find("div", class_="detail-text")
        if not content_div:
            content_div = soup.find("div", class_="detail_text")
        if not content_div:
            content_div = soup.find("article")
        if not content_div:
            print(f"Tidak menemukan container konten")
            return ""
        for unwanted in content_div.find_all(["script", "style", "iframe"]):
            unwanted.decompose()
        divs_to_remove = []
        for div in content_div.find_all("div"):
            if div is None:
                continue
            class_list = div.get("class", [])
            if class_list is None:
                continue
            class_str = " ".join(class_list) if isinstance(class_list, list) else str(class_list)
            if any(x in class_str for x in ["ads", "related", "sisip", "baca", "lihatjg", "linksisip"]):
                divs_to_remove.append(div)
        for div in divs_to_remove:
            if div is not None:
                div.decompose()        
        tables_to_remove = []
        for table in content_div.find_all("table"):
            if table is None:
                continue
            class_list = table.get("class", [])
            if class_list is None:
                continue
            class_str = " ".join(class_list) if isinstance(class_list, list) else str(class_list)
            if any(x in class_str for x in ["linksisip", "pic_artikel"]):
                tables_to_remove.append(table)
        for table in tables_to_remove:
            if table is not None:
                table.decompose()
        all_text_lines = []
        for p in content_div.find_all("p"):
            if p is None:
                continue
            text = p.get_text(strip=True)
            if text and len(text) > 15:
                cleaned_text = clean_content_text(text)
                if cleaned_text:
                    all_text_lines.append(cleaned_text)
        for ol in content_div.find_all(["ol", "ul"]):
            if ol is None:
                continue
            for li in ol.find_all("li", recursive=False):
                if li is None:
                    continue
                text = li.get_text(strip=True)
                if text and len(text) > 15:
                    all_text_lines.append(text)
        result = "\n\n".join(all_text_lines)
        print(f"Konten: {len(result)} karakter")
        return result
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return ""

def scrape_cnbc_all_pages(query: str, filter_date: str = None, headless=True, max_pages=None):
    driver = setup_driver(headless=headless)
    try:
        base_url = "https://www.cnbcindonesia.com"
        search_url = f"{base_url}/search?query={query}"
        filter_datetime = None
        if filter_date:
            try:
                if re.match(r"\d{4}-\d{2}-\d{2}", filter_date):
                    filter_datetime = datetime.strptime(filter_date, "%Y-%m-%d")
                else:
                    filter_datetime = datetime.strptime(filter_date, "%d %b %Y")
                print(f"\nTanggal target: {filter_datetime.strftime('%d %b %Y')}")
            except Exception as e:
                print(f"Error parsing date: {e}")
        all_results, soup_first = parse_cnbc_page_with_selenium(driver, search_url)
        if not soup_first:
            print("Gagal mengakses halaman pertama")
            return []
        pagination = find_pagination_container_by_pattern(soup_first)
        total_pages = get_total_pages_from_pagination(pagination)
        if max_pages:
            total_pages = min(total_pages, max_pages)        
        should_stop = False
        if filter_datetime and all_results:
            filtered_results = []
            for r in all_results:
                try:
                    article_date = datetime.strptime(r["date"], "%d %b %Y")
                    if article_date < filter_datetime:
                        should_stop = True
                        break
                    elif article_date == filter_datetime:
                        filtered_results.append(r)
                        print(f"Match: {r['date']}")
                    else:
                        print(f"Skip: {r['date']} > target")    
                except Exception as e:
                    print(f"Error: {r['date']} → {e}")
            all_results = filtered_results
            print(f"Lolos halaman 1: {len(all_results)} artikel")
            if should_stop:
                print(f"\nArtikel di halaman 1 sudah lebih lama dari target")
                print(f"Tidak melanjutkan ke halaman berikutnya")
        if not should_stop and total_pages > 1:
            for page_num in range(2, total_pages + 1):
                next_url = f"{search_url}&page={page_num}"
                page_results, _ = parse_cnbc_page_with_selenium(driver, next_url)
                if not page_results:
                    print(f"Tidak ada hasil, berhenti")
                    break
                if filter_datetime:
                    print(f"\nMemfilter artikel di halaman {page_num}...")
                    matching_results = []
                    for r in page_results:
                        try:
                            article_date = datetime.strptime(r["date"], "%d %b %Y")
                            if article_date < filter_datetime:
                                should_stop = True
                                break
                            elif article_date == filter_datetime:
                                matching_results.append(r)
                            else:
                                print(f"Skip: {r['date']} > target")      
                        except:
                            pass
                    print(f"Lolos halaman {page_num}: {len(matching_results)} artikel")
                    all_results.extend(matching_results)
                    if should_stop:
                        print(f"\nEARLY STOPPING at halaman {page_num}")
                        break 
                else:
                    all_results.extend(page_results)
                time.sleep(1)
        print(f"\n{'='*70}")
        print(f"RINGKASAN")
        print(f"{'='*70}")
        print(f"Total artikel ditemukan: {len(all_results)}")
        print(f"{'='*70}")
        if not all_results:
            return []
        print(f"\n{'='*70}")
        print(f"MENGAMBIL KONTEN")
        print(f"{'='*70}")
        for i, article in enumerate(all_results, 1):
            print(f"\n[{i}/{len(all_results)}] {article['title'][:65]}...")
            konten = scrape_cnbc_article_content_selenium(driver, article['link'])
            article['content'] = konten
            time.sleep(0.5)
        print(f"\nSELESAI!")
        return all_results
    except Exception as e:
        traceback.print_exc()
        return []  
    finally:
        driver.quit()

def main_cnbc(keyword: str, tanggal: str = None, headless=True, max_pages=None):
    if tanggal is None:
        tanggal = datetime.now().strftime("%d %b %Y")
    else:
        if re.match(r"\d{2}-\d{2}-\d{4}", tanggal):  
            try:
                temp_date = datetime.strptime(tanggal, "%d-%m-%Y")
                tanggal = temp_date.strftime("%d %b %Y")
            except:
                pass
    results = scrape_cnbc_all_pages(
        query=keyword, 
        filter_date=tanggal, 
        headless=headless,
        max_pages=max_pages
    )
    if not results:
        print("\nTidak ada hasil ditemukan")
        return None
    df = pd.DataFrame(results)
    df['date'] = pd.to_datetime(df['date'], format="%d %b %Y", errors='coerce')
    df['date'] = df['date'].dt.date
    df = df.rename(columns={'link': 'url'})
    print(f"\n{'='*70}")
    print(f"DATAFRAME INFO")
    print(f"{'='*70}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"{'='*70}")
    print("\nPreview:")
    print(df[['title', 'date']].head(10))
    return df

if __name__ == "__main__":
    df = main_cnbc(
        keyword="emas",
        tanggal="02-02-2026"
    )
    
    if df is not None and len(df) > 0:
        print(f"\n{'='*70}")
        print(f"HASIL AKHIR")
        print(f"{'='*70}")
        print(f"Total artikel: {len(df)}")
        print(f"\nSample konten:")
        if len(df) > 0 and 'content' in df.columns:
            print(df.iloc[0]['content'][:300] + "...")
        df.to_excel("cnbc_id.xlsx")




 