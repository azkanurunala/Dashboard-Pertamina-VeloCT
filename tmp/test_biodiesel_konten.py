"""
Lihat konten penuh artikel ESDM Biodiesel untuk extract pola HIP.
"""
import asyncio, sys, re, aiohttp
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')

API_URL = "https://ebtke.esdm.go.id/api/api/artikel?kategori_slug=pengumuman&start=0&length=30&is_published=true"

def extract_month_from_title(title):
    """Extract bulan dan tahun dari judul artikel."""
    m = re.search(
        r'Bulan\s+(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+(\d{4})',
        title, re.IGNORECASE
    )
    if m:
        return f"{m.group(1)} {m.group(2)}"
    return None

def extract_hip_from_konten(konten):
    """Coba berbagai pola untuk extract nilai HIP dari HTML konten."""
    import html
    text = html.unescape(re.sub('<[^>]+>', ' ', konten))
    text = re.sub(r'\s+', ' ', text).strip()

    # Pola: angka 4-5 digit (nilai ribuan IDR/liter), preceded by RUPIAH/LITER or just standalone
    # Typical: "Rp 14.123/liter" atau "14.123" atau "14,123"
    patterns = [
        r'(?:Rp\.?\s*)([\d]{2}[\.\,][\d]{3})\s*(?:/\s*[Ll]iter)',
        r'([\d]{2}[\.\,][\d]{3})\s*/\s*[Ll]iter',
        r'(?:sebesar|ditetapkan|HIP)[^0-9]+([\d]{2}[\.\,][\d]{3})',
        r'RUPIAH/LITER.*?([\d]{2}[\.\,][\d]{3})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(1).replace('.', '').replace(',', '')
            return int(val), pat

    # fallback: semua angka 5 digit (seperti 14123 atau 16000)
    all_nums = re.findall(r'\b(1[0-9]{4})\b', text)
    return all_nums[:5], 'fallback'

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json()

        articles = data.get('data', [])
        biodiesel = [a for a in articles if all(k in a.get('judul','').upper() for k in ['HIP','BBN','JENIS','BIODIESEL','BULAN'])]

        for a in biodiesel[:6]:
            title = a['judul']
            konten = a.get('konten', '')
            month = extract_month_from_title(title)
            hip, pat = extract_hip_from_konten(konten)

            print(f"\n[{a.get('tanggal_publikasi','')[:10]}] {title}")
            print(f"  Bulan  : {month}")
            print(f"  HIP    : {hip}  (pattern: {pat})")
            if not isinstance(hip, int):
                # Show relevant text snippet
                import html as htmlmod
                text = htmlmod.unescape(re.sub('<[^>]+>', ' ', konten))
                # Find numbers and context
                idx = text.find('RUPIAH')
                if idx < 0: idx = text.find('Rp')
                if idx >= 0:
                    print(f"  snippet: ...{text[max(0,idx-20):idx+100]}...")
                # Also show last 300 chars
                print(f"  tail   : ...{text[-300:]}")

asyncio.run(main())
