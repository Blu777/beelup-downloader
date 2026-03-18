import urllib.request
import re

ID = '26745803'
urls_to_try = [
    f'https://beelup.com/partido/{ID}',
    f'https://beelup.com/{ID}',
    f'https://beelup.com/watch?v={ID}',
    f'https://beelup.com/partido?id={ID}',
    f'https://beelup.com/app/partido.php?id={ID}',
]

def check():
    with open('urls_out.txt', 'w', encoding='utf-8') as f:
        for url in urls_to_try:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req) as r:
                    html = r.read().decode('utf-8', errors='ignore')
                    f.write(f"[OK] {url}\n")
                    
                    dates = set(re.findall(r'\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2}', html))
                    if dates:
                        f.write(f"  Dates: {dates}\n")
                    else:
                        f.write("  No dates found.\n")
                        
                    for line in html.split('\n'):
                        lower_line = line.lower()
                        if 'fecha' in lower_line or 'date' in lower_line or '2025' in lower_line or '2024' in lower_line or '2026' in lower_line:
                            if len(line.strip()) < 200:
                                f.write(f"  Line: {line.strip()}\n")
            except Exception as e:
                f.write(f"[Error] {url}: {e}\n")

if __name__ == '__main__':
    check()
