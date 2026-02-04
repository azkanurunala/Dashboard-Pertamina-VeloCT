import re
import time
import json
from datetime import datetime
import requests
import feedparser
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Common Tempo article URLs:
# - https://xxx.tempo.co/read/2084660/slug
# - https://www.tempo.co/hukum/slug-2112318
# + tolerant of trailing slashes dan queries
ARTICLE_URL_RE = re.compile(
    r"^https?://([a-z0-9-]+\.)?tempo\.co/.*(/read/\d+/|-\d{6,})(/)?($|\?)", 
    re.I
)

TEMPO_FEEDS = [
    "https://rss.tempo.co/",
    "https://rss.tempo.co/full-content/",
    "https://rss.tempo.co/nasional",
    "https://rss.tempo.co/bisnis",
    "https://rss.tempo.co/metro",
    "https://rss.tempo.co/dunia",
    "https://rss.tempo.co/bola",
    "https://rss.tempo.co/tekno",
    "https://rss.tempo.co/otomotif",
    "https://rss.tempo.co/seleb",
    "https://rss.tempo.co/gaya",
    "https://rss.tempo.co/travel",
    "https://rss.tempo.co/difabel",
    "https://rss.tempo.co/creativelab",
    "https://rss.tempo.co/inforial",
    "https://rss.tempo.co/event",
    "https://rss.tempo.co/politik",
    "https://rss.tempo.co/hukum",
    "https://rss.tempo.co/ekonomi",
    "https://rss.tempo.co/lingkungan",
    "https://rss.tempo.co/wawancara",
    "https://rss.tempo.co/sains",
    "https://rss.tempo.co/investigasi",
    "https://rss.tempo.co/cekfakta",
    "https://rss.tempo.co/kolom",
    "https://rss.tempo.co/hiburan",
    "https://rss.tempo.co/internasional",
    "https://rss.tempo.co/otomotif",
    "https://rss.tempo.co/olahraga",
    "https://rss.tempo.co/sepakbola",
    "https://rss.tempo.co/digital",
    "https://rss.tempo.co/gaya-hidup"
]

# ======================
# UTILS
# ======================
def normalize_date(tanggal: str | None) -> str | None:
    """
    Normalize dstes to the YYYY-MM-DD format.
    Accepts input:
      - None
      - "DD-MM-YYYY"
      - "YYYY-MM-DD"
    """
    if not tanggal:
        return None
    t = str(tanggal).strip()
    if re.match(r"^\d{2}-\d{2}-\d{4}$", t):
        dd, mm, yy = t.split("-")
        return f"{yy}-{mm}-{dd}"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", t):
        return t
    return t

def dedup_by_key(items, key):
    seen = set()
    out = []
    for it in items:
        v = it.get(key)
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(it)
    return out


# ======================
# LISTING SOURCES
# ======================
def fetch_rss_entries(feed_url, limit=50):
    r = requests.get(feed_url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    feed = feedparser.parse(r.content)
    
    print(f"[RSS] {feed_url} -> entries: {len(feed.entries)}")
    
    for i, e in enumerate(feed.entries[:3], 1):
        t = getattr(e, "title", "")
        # print(f"sample_{i}: {t[:80]}")
                
    items = []
    for entry in feed.entries[:limit]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

        date = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            dt = datetime(*entry.published_parsed[:6])
            date = dt.strftime("%Y-%m-%d")
        
        items.append({"title": title, "link": link, "tanggal": date, "summary": summary})
    return items

def search_tempo_internal_selenium(keyword, start_date=None, end_date=None, max_pages=3, headless=True):
    """
    Search Tempo via Selenium (render JS).
    Return: (urls, status) status: ok|blocked|changed|error
    """
    kw_enc = requests.utils.quote(keyword.strip())
    urls_all = []

    # build base url
    def build_url(page):
        url = f"https://www.tempo.co/search?page={page}&q={kw_enc}"
        if start_date and end_date:
            url += f"&start_date={start_date}&end_date={end_date}"
        return url

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1280,900")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        for page in range(1, max_pages + 1):
            url = build_url(page)
            # print(f"[SEARCH/SEL] OPEN {url}")
            driver.get(url)

            time.sleep(3) 

            anchors = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            print(f"[SEARCH/SEL] total <a>={len(anchors)}")

            samples = []
            for a in anchors[:30]:
                h = a.get_attribute("href")
                if h and "tempo.co" in h:
                    samples.append(h)
                if len(samples) >= 8:
                    break

            page_urls = []
            for a in anchors:
                href = a.get_attribute("href")
                if not href:
                    continue
                href = href.split("#")[0].strip()
                if ARTICLE_URL_RE.match(href):
                    page_urls.append(href)

            # dedup per page
            seen = set()
            page_urls_unique = []
            for u in page_urls:
                if u not in seen:
                    seen.add(u)
                    page_urls_unique.append(u)

            sample = page_urls_unique[0] if page_urls_unique else "-"
            # print(f"[SEARCH/SEL] page={page} article_urls={len(page_urls_unique)} sample={sample}")

            if not page_urls_unique:
                if page == 1:
                    return [], "changed"
                break

            urls_all.extend(page_urls_unique)
            time.sleep(1)

        # global dedup
        seen2 = set()
        final = []
        for u in urls_all:
            if u not in seen2:
                seen2.add(u)
                final.append(u)

        return final, "ok"

    except Exception as e:
        print(f"[SEARCH/SEL] ERROR: {e}")
        return [], "error"

    finally:
        if driver:
            driver.quit()
 
# ======================
# DETAIL EXTRACTION
# ======================
def ekstrak_meta_tempo(url):
    """
    Get the title and date from the article page.
    Priority: JSON-LD -> meta article: published_time -> fallback <title>
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        title = ""
        date = ""

        # 1) JSON-LD
        for tag in soup.find_all("script", type="application/ld+json"):
            txt = (tag.string or "").strip()
            if not txt:
                continue
            try:
                data = json.loads(txt)
            except Exception:
                continue

            candidates = data if isinstance(data, list) else [data]
            for obj in candidates:
                if isinstance(obj, dict) and obj.get("@type") in ("NewsArticle", "Article"):
                    title = obj.get("headline") or obj.get("name") or title
                    dt = obj.get("datePublished") or obj.get("dateCreated") or ""
                    if dt:
                        date = dt.split("T")[0]
                    break
            if title or date:
                break

        # 2) meta published_time
        if not date:
            m = soup.find("meta", property="article:published_time")
            if m and m.get("content"):
                date = m["content"].split("T")[0]

        # 3) og:title / title fallback
        if not title:
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                title = og["content"].strip()
            elif soup.title:
                title = soup.title.get_text(strip=True)

        return title.strip(), date.strip()
    except Exception:
        return "", ""
  
def ambil_konten_artikel_tempo(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        s = BeautifulSoup(r.text, 'html.parser')
        teks_final = []

        kontainer = s.select_one('div#isi, div.detail-content, article, div.detail-area')
        if not kontainer:
            kontainer = s

        for tag in kontainer.select('script, style, iframe, figure, aside, nav, '
                                    'div[class*="ad"], div[class*="iklan"], '
                                    'div[class*="share"], div[class*="related"], '
                                    'div[class*="author"], div[class*="penulis"], '
                                    'div.text-neutral-900'):
            tag.decompose()

        for p in kontainer.find_all('p'):
            teks = re.sub(r'\s+', ' ', p.get_text(" ", strip=True))
            if len(teks) > 30:
                teks_final.append(teks)

        teks_bersih = "\n\n".join(teks_final)
        pola_bersih = [
            r'Baca berita.*?klik di sini',
            r'Scroll ke bawah.*',
            r'Lulus dari Jurusan.*?(hak asasi manusia)?',
            r'This is breaking news.*'
        ]
        for pola in pola_bersih:
            teks_bersih = re.sub(pola, '', teks_bersih, flags=re.I)
        teks_bersih = re.sub(r'\s+', ' ', teks_bersih).strip()

        return teks_bersih if teks_bersih else "N/A"
    except:
        return "N/A"
  
# ======================
# ORCHESTRATOR
# ======================
def scrape_tempo(keyword, tanggal=None, rss_limit=80):
    kw = keyword.lower().strip()
    
    if tanggal:
        tanggal = str(tanggal).strip()
        if re.match(r"^\d{2}-\d{2}-\d{4}$", tanggal):
            dd, mm, yy = tanggal.split("-")
            tanggal = f"{yy}-{mm}-{dd}"
    
    print(f"[INFO] keyword='{kw}' | tanggal_filter='{tanggal}' | rss_limit={rss_limit}")

    hasil = [] 
    urls, status = search_tempo_internal_selenium(
        keyword,
        start_date=tanggal,  
        end_date=tanggal,
        max_pages=3,
        headless=True
    )

    if status == "ok" and urls:
        print(f"[INFO] search OK: {len(urls)} urls")
        for u in urls:
            # print(f"[META] fetching meta: {u}")
            title, tgl = ekstrak_meta_tempo(u)
            # print(f"[META] got title_len={len(title)} | tgl='{tgl}'")

            if tanggal:
                if not tgl:
                    print(f"[SKIP] tanggal_filter='{tanggal}' tapi meta tgl kosong -> {u}")
                    continue
                if tgl != tanggal:
                    print(f"[SKIP] tgl meta '{tgl}' != filter '{tanggal}' -> {u}")
                    continue


            hasil.append({"title": title, "link": u, "tanggal": tgl})
    else:
        print(f"[INFO] search FAILED: status={status}, fallback to RSS")

        for feed_url in TEMPO_FEEDS:
            try:
                entries = fetch_rss_entries(feed_url, limit=rss_limit)
            except Exception:
                continue

            for e in entries:
                title = e.get("title", "")
                link = e.get("link", "")
                tgl  = e.get("tanggal", "")
                text = (title + " " + (e.get("summary","") or "")).lower()

                if not link:
                    continue
                
                if kw not in text:
                    continue
                
                if tanggal and tgl and tgl != tanggal:
                    continue

                hasil.append({"title": title, "link": link, "tanggal": tgl})

    # dedup URL
    seen = set()
    hasil_unique = []
    for a in hasil:
        if a["link"] and a["link"] not in seen:
            seen.add(a["link"])
            hasil_unique.append(a)

    if not hasil_unique:
        print("[RESULT] 0 artikel ditemukan (search + RSS fallback).")
        return []
    
    print(f"Ditemukan {len(hasil_unique)} artikel. Mengambil konten...")

    hasil_bersih = []
    for idx, a in enumerate(hasil_unique, 1):
        # print(f"[FETCH] ({idx}/{len(hasil_unique)}) {a['link']}")        
        konten = ambil_konten_artikel_tempo(a['link'])
        time.sleep(1.0)

        hasil_bersih.append({
            'title': a.get('title', ''),
            'date': a.get('tanggal', ''),
            'url': a.get('link', ''),
            'content': konten
        })

    return hasil_bersih


# ======================
# MAIN
# ======================
if __name__ == "__main__":
    data = scrape_tempo("minyak", tanggal=None)
    df = pd.DataFrame(data)
    print(df.head())
    