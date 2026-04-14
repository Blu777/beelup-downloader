<<<<<<< HEAD
import urllib.request
import re

maps_urls = {
    "CONTAINER RAMOS MEJIA": "https://maps.app.goo.gl/UAxW1AMBuKnL2ezQ9",
    "MEGAFUTBOL": "https://maps.app.goo.gl/TGmHd6uCHv6Ts5Ja9"
}

def check():
    for name, url in maps_urls.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req) as r:
                html = r.read().decode('utf-8', errors='ignore')
                m = re.search(r'meta content="([^"]+\.jpg[^"]*)" property="og:image"', html)
                if m:
                    print(f"{name}: {m.group(1)}")
                else:
                    m2 = re.search(r'meta content="([^"]+)" property="og:image"', html)
                    if m2:
                        print(f"{name}: {m2.group(1)}")
                    else:
                        print(f"{name}: No image found")
        except Exception as e:
            print(f"Error {name}: {e}")

if __name__ == '__main__':
    check()
=======
import urllib.request
import re

maps_urls = {
    "CONTAINER RAMOS MEJIA": "https://maps.app.goo.gl/UAxW1AMBuKnL2ezQ9",
    "MEGAFUTBOL": "https://maps.app.goo.gl/TGmHd6uCHv6Ts5Ja9"
}

def check():
    for name, url in maps_urls.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req) as r:
                html = r.read().decode('utf-8', errors='ignore')
                m = re.search(r'meta content="([^"]+\.jpg[^"]*)" property="og:image"', html)
                if m:
                    print(f"{name}: {m.group(1)}")
                else:
                    m2 = re.search(r'meta content="([^"]+)" property="og:image"', html)
                    if m2:
                        print(f"{name}: {m2.group(1)}")
                    else:
                        print(f"{name}: No image found")
        except Exception as e:
            print(f"Error {name}: {e}")

if __name__ == '__main__':
    check()
>>>>>>> 5373f1b (local changes)
