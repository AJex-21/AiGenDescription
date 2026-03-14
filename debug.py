import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
})

url = "https://www.kjell.com/se/produkter/mobilt/mobilladdare/usb-laddare/linocell-gan-multiladdare-33-w-pd-vit-p22191"
response = session.get(url, timeout=15)

print("Status code:", response.status_code)
print("Response length:", len(response.text))
print("Has CURRENT_PAGE:", "window.CURRENT_PAGE" in response.text)
print("First 1000 chars:", response.text[:1000])

url = "https://www.kjell.com/se/produkter/mobilt/mobilladdare/usb-laddare/linocell-gan-multiladdare-33-w-pd-vit-p22191"
response = session.get(url, timeout=15)

marker = "window.CURRENT_PAGE = "
idx = response.text.find(marker)
print("Marker found at index:", idx)
print("Characters around it:", repr(response.text[idx:idx+100]))
