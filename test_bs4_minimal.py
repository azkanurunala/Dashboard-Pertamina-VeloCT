
from bs4 import BeautifulSoup
import os

html = '<table id="sitemap"><tr><th>URL</th><th>Type</th><th>Mod</th></tr><tr><td><a href="http://test.com">Test</a></td><td>page</td><td>2024-01-01</td></tr></table>'
soup = BeautifulSoup(html, 'html.parser')
table = soup.find('table', id='sitemap')
rows = table.find_all('tr')[1:]
print(f"Extracted {len(rows)} rows")
for row in rows:
    tds = row.find_all('td')
    url = tds[0].find('a').get('href')
    date = tds[2].get_text()[:10]
    print(f"URL: {url}, Date: {date}")
