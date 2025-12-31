import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re
import locale
import time

locale.setlocale(locale.LC_TIME, "C")

def clean_date_cnbc(raw_date: str) -> str:
    now = datetime.now()
    raw_date_original = raw_date
    raw_date = raw_date.strip().lower()

    if match_tahun := re.search(r"(\d+)\s*tahun", raw_date):
        years_ago = int(match_tahun.group(1))
        target_date = now - timedelta(days=years_ago * 365)
        result = target_date.strftime("%d %b %Y")
        print(f" [DATE] '{raw_date_original}' → '{result}' ({years_ago} tahun lalu)")
        return result

    if match_bulan := re.search(r"(\d+)\s*bulan", raw_date):
        months_ago = int(match_bulan.group(1))
        target_date = now - timedelta(days=months_ago * 30)
        result = target_date.strftime("%d %b %Y")
        print(f" [DATE] '{raw_date_original}' → '{result}' ({months_ago} bulan lalu)")
        return result

    if match_minggu := re.search(r"(\d+)\s*minggu", raw_date):
        weeks_ago = int(match_minggu.group(1))
        target_date = now - timedelta(weeks=weeks_ago)
        result = target_date.strftime("%d %b %Y")
        print(f" [DATE] '{raw_date_original}' → '{result}' ({weeks_ago} minggu lalu)")
        return result

    if match_hari := re.search(r"(\d+)\s*hari", raw_date):
        days_ago = int(match_hari.group(1))
        target_date = now - timedelta(days=days_ago)
        result = target_date.strftime("%d %b %Y")
        print(f" [DATE] '{raw_date_original}' → '{result}' ({days_ago} hari lalu)")
        return result

    if "yang lalu" in raw_date:
        match_jam = re.search(r"(\d+)\s*jam", raw_date)
        hours_ago = int(match_jam.group(1)) if match_jam else 0
        match_menit = re.search(r"(\d+)\s*menit", raw_date)
        minutes_ago = int(match_menit.group(1)) if match_menit else 0
        delta = timedelta(hours=hours_ago, minutes=minutes_ago)
        target_datetime = now - delta
        result = target_datetime.strftime("%d %b %Y")
        print(f" [DATE] '{raw_date_original}' → '{result}' ({hours_ago}h {minutes_ago}m yang lalu)")
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

    print(f" [DATE] '{raw_date_original}' → '{raw_date}' (tidak bisa parse)")
    return raw_date

def get_total_pages_cnbc(soup) -> int:
    try:
        pagination = soup.find("div", class_="flex gap-1 items-center justify-center m-0")
        if not pagination:
            all_links = soup.find_all("a", href=re.compile(r"[?&]page=\d+"))
            if not all_links:
                return 1
            page_links = all_links
        else:
            page_links = pagination.find_all("a", href=True)

        nums = []
        for a in page_links:
            href = a.get("href", "")
            match = re.search(r"[?&]page=(\d+)", href)
            if match:
                nums.append(int(match.group(1)))
            text = a.get_text(strip=True)
            if text.isdigit():
                nums.append(int(text))
        return max(nums) if nums else 1
    except:
        return 1

def parse_cnbc_page_list(url: str, headers: dict):
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"Gagal mengakses: {url}")
        return [], None

    soup = BeautifulSoup(r.text, "html.parser")
    articles = soup.find_all("article")
    page_results = []

    for idx, article in enumerate(articles, 1):
        try:
            link_tag = article.find("a", class_="group", href=True)
            if not link_tag:
                continue

            link = link_tag.get("href", "")
            if link.startswith("/"):
                link = "https://www.cnbcindonesia.com" + link

            title_tag = link_tag.find("h2")
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)

            date_tag = link_tag.find("span", class_="text-xs text-gray")
            raw_date = date_tag.get_text(strip=True) if date_tag else ""

            print(f" [{idx}] {title[:50]}...")
            pub_date = clean_date_cnbc(raw_date) if raw_date else ""

            page_results.append({
                "title": title,
                "date": pub_date,
                "link": link,
            })
        except Exception as e:
            print(f" [{idx}] Error: {e}")
            continue

    return page_results, soup

def scrape_cnbc_article_content(url: str, headers: dict) -> str:
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        content_div = soup.find("div", class_="detail-text")
        if not content_div:
            content_div = soup.find("div", class_="detail_text")
        
        if not content_div:
            print(f"Tidak menemukan div konten")
            return ""

        for unwanted in content_div.find_all(["script", "style", "iframe", "figure", "table"]):
            unwanted.decompose()

        for div in content_div.find_all("div"):
            class_str = " ".join(div.get("class", []))
            if any(x in class_str for x in ["ads", "related", "sisip", "baca", "lihatjg", "linksisip"]):
                div.decompose()

        all_text_lines = []
        
        for p in content_div.find_all("p"):
            text = p.get_text(strip=True)
            if text and len(text) > 15:
                if text.startswith("Jakarta, CNBC Indonesia"):
                    text = text.replace("Jakarta, CNBC Indonesia - ", "")
                    text = text.replace("Jakarta, CNBC Indonesia-", "")
                
                if text.startswith("(") and text.endswith(")") and len(text) < 20:
                    continue
                
                all_text_lines.append(text)

        for ol in content_div.find_all(["ol", "ul"]):
            for li in ol.find_all("li", recursive=False):
                text = li.get_text(strip=True)
                if text and len(text) > 15:
                    all_text_lines.append(text)

        result = "\n\n".join(all_text_lines)
        
        if not result:
            print(f"Konten kosong setelah parsing")
        else:
            print(f"Konten diambil: {len(result)} karakter")
        
        return result
        
    except Exception as e:
        print(f"Error scraping konten: {e}")
        return ""

def scrape_cnbc_all(query: str, headers: dict, filter_date: str = None):
    base_url = "https://www.cnbcindonesia.com"
    search_base = f"{base_url}/search?query={query}"

    filter_datetime = None
    if filter_date:
        try:
            filter_datetime = datetime.strptime(filter_date, "%d %b %Y")
            print(f"Filter tanggal: {filter_datetime.strftime('%d %b %Y')}")
        except:
            pass

    print(f"\nMengambil halaman 1...")
    all_results, soup_first = parse_cnbc_page_list(search_base, headers)
    if not soup_first:
        print("Gagal mengakses halaman pertama")
        return []

    total_pages = get_total_pages_cnbc(soup_first)
    print(f"Total halaman: {total_pages}")
    print(f"Artikel di halaman 1: {len(all_results)}")

    should_stop = False
    if filter_datetime and all_results:
        print(f"\nFiltering berdasarkan tanggal target: {filter_datetime.strftime('%d %b %Y')}")
        filtered_page1 = []
        for r in all_results:
            try:
                article_date = datetime.strptime(r["date"], "%d %b %Y")
                comparison = "SESUAI" if article_date == filter_datetime else ("LEBIH BARU" if article_date > filter_datetime else "LEBIH LAMA")
                print(f" • {r['date']} vs {filter_datetime.strftime('%d %b %Y')} → {comparison}")

                if article_date < filter_datetime:
                    print(f" → Early stopping triggered!")
                    should_stop = True
                    break
                elif article_date == filter_datetime:
                    filtered_page1.append(r)
            except Exception as e:
                print(f" • Error parse: {r['date']} → {e}")
        all_results = filtered_page1
        print(f"\nArtikel lolos filter di halaman 1: {len(all_results)}")
    else:
        print("Tidak ada filter tanggal")

    if not should_stop and total_pages > 1:
        for page_num in range(2, total_pages + 1):
            print(f"Mengambil halaman {page_num}/{total_pages}...")
            next_url = f"{search_base}&page={page_num}"
            page_results, _ = parse_cnbc_page_list(next_url, headers)
            if not page_results:
                break

            if filter_datetime:
                matching_results = []
                for r in page_results:
                    try:
                        article_date = datetime.strptime(r["date"], "%d %b %Y")
                        if article_date < filter_datetime:
                            should_stop = True
                            break
                        elif article_date == filter_datetime:
                            matching_results.append(r)
                    except:
                        pass
                all_results.extend(matching_results)
                if should_stop:
                    print(f"Early stopping di halaman {page_num}")
                    break
            else:
                all_results.extend(page_results)

            time.sleep(1)

    print(f"\nTotal artikel yang lolos: {len(all_results)}")
    if not all_results:
        return []

    print(f"Mengambil konten {len(all_results)} artikel...")
    for i, article in enumerate(all_results, 1):
        print(f"[{i}/{len(all_results)}] {article['title'][:50]}...")
        konten = scrape_cnbc_article_content(article['link'], headers)
        article['konten'] = konten
        time.sleep(0.5)

    print("Selesai!")
    return all_results

def main_cnbc(keyword: str, tanggal: str = None):
    if tanggal is None:
        tanggal = datetime.now().strftime("%d %b %Y")
    else:
        if re.match(r"\d{4}-\d{2}-\d{2}", tanggal):
            try:
                temp_date = datetime.strptime(tanggal, "%Y-%m-%d")
                tanggal = temp_date.strftime("%d %b %Y")
            except:
                pass

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    }

    print(f"\n{'='*60}")
    print(f"SCRAPING CNBC INDONESIA")
    print(f"Keyword: {keyword}")
    print(f"Tanggal: {tanggal}")
    print(f"{'='*60}")

    results = scrape_cnbc_all(keyword, headers, filter_date=tanggal)
    if not results:
        print("\nTidak ada hasil ditemukan")
        return None

    df = pd.DataFrame(results)
    df['date'] = pd.to_datetime(df['date'], format="%d %b %Y", errors='coerce')
    df['date'] = df['date'].dt.date
    df = df.rename(columns={'konten': 'content', 'link': 'url'})

    print(f"\nDataFrame shape: {df.shape}")
    print(df[['title', 'date']].head())

    return df

if __name__ == "__main__":
    df = main_cnbc(keyword="kurs", tanggal="2025-12-21")
    if df is not None and len(df) > 0:
        output_file = f"cnbc_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\nData berhasil disimpan ke: {output_file}")
        print(f"Total artikel: {len(df)}")
        print("\nPreview data:")
        print(df[['title', 'date']].to_string())
    else:
        print("\nTidak ada data untuk disimpan")