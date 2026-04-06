"""
Debug: cek konten artikel ESDM Biodiesel (Jan–Apr 2026) dan coba extract HIP dari HTML.
"""
import asyncio, sys, re, aiohttp
sys.path.insert(0, r'c:\RunningProjects\Dashboard-Pertamina-VeloCT\azure_functions')

API_URL = "https://ebtke.esdm.go.id/api/api/artikel?kategori_slug=pengumuman&start=0&length=30&is_published=true"

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(API_URL, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.json()

        articles = data.get('data', [])
        biodiesel = [a for a in articles if all(k in a.get('judul','').upper() for k in ['HIP','BBN','JENIS','BIODIESEL','BULAN'])]
        print(f"Total biodiesel articles: {len(biodiesel)}")

        for a in biodiesel:
            title = a['judul']
            konten = a.get('konten', '')
            slug = a.get('slug', '')
            date = a.get('tanggal_publikasi') or a.get('tgl_upload','')

            # Semua link dalam konten
            links = re.findall(r'href=["\']([^"\']+)["\']', konten)
            pdf_links = [l for l in links if 'drive.esdm' in l or '.pdf' in l.lower()]

            # Coba extract angka HIP dari konten HTML
            # Typical: Rp 16.062/liter atau angka ribuan
            hip_matches = re.findall(r'(?:Rp\.?\s*|IDR\s*)?([\d]{4,6}(?:[.,]\d+)?)\s*(?:/liter|rupiah|rp)', konten, re.IGNORECASE)
            # Also try table-like patterns
            table_matches = re.findall(r'>\s*([\d]{4,6}(?:[.,]\d+)?)\s*<', konten)

            print(f"\n[{date[:10]}] {title}")
            print(f"  links    : {pdf_links}")
            print(f"  hip_match: {hip_matches[:5]}")
            print(f"  tbl_match: {table_matches[:5]}")
            # Show raw konten snippet
            if konten:
                print(f"  konten   : {konten[:300]}")
            else:
                # Fetch article page directly
                url = f"https://ebtke.esdm.go.id/artikel/pengumuman/{slug}"
                print(f"  Fetching page: {url}")
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                        html = await r.text()
                    # Look for HIP in page
                    hip2 = re.findall(r'(?:Rp\.?\s*)?([\d]{4,6}(?:[.,]\d+)?)\s*/\s*[Ll]iter', html)
                    links2 = re.findall(r'href=["\']([^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE)
                    links3 = re.findall(r'href=["\']([^"\']*drive\.esdm[^"\']*)["\']', html)
                    print(f"  page hip : {hip2[:5]}")
                    print(f"  page pdf : {links2[:3]}")
                    print(f"  page drv : {links3[:3]}")
                    print(f"  html snip: {html[html.find('HIP') if 'HIP' in html else 0:html.find('HIP')+300 if 'HIP' in html else 300]}")
                except Exception as e:
                    print(f"  page err : {e}")

asyncio.run(main())
