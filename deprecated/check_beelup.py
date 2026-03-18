import urllib.request
import json

URL_JSON = 'https://beelup.com/obtener.video.playlist.php?id=26745803&formato=json'

try:
    req = urllib.request.Request(URL_JSON, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as r:
        raw = r.read().decode('utf-8')
        data = json.loads(raw)
        with open('beelup_info.txt', 'w', encoding='utf-8') as f:
            f.write("JSON keys:\n")
            for k in data.keys():
                f.write(k + "\n")
            f.write("\nKey Values:\n")
            for k, v in data.items():
                if k != 'segmentos':
                    f.write(f"{k} = {v}\n")
except Exception as e:
    with open('beelup_info.txt', 'w', encoding='utf-8') as f:
        f.write("Error fetching JSON: " + str(e))
