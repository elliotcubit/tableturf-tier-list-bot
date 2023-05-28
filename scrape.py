from bs4 import BeautifulSoup
import requests
import json
import time

root = "https://splatoonwiki.org"
parent_endpoint = "/wiki/Tableturf_Battle"

def get(s: str):
    print(f"GET {s}")
    time.sleep(0.1)
    return requests.get(s)

def main():
    resp = get(root + parent_endpoint)
    if resp.status_code != 200:
        print(f"non-200 code: {resp.status_code}")
        return
    soup = BeautifulSoup(resp.content, features="html.parser")
    start = soup.find(id="Sleeves")
    inner = u""
    for elt in start.parent.nextSiblingGenerator():
        if elt.name == "h3":
            break
        inner += str(elt)
    soup = BeautifulSoup(inner, features="html.parser")
    out = {}
    for idx, it in enumerate(soup.find_all("li", attrs={"class": "gallerybox"})):
        for (nametag, linktag) in zip(it.find_all("div", attrs={"class":"gallerytext"}), it.find_all("a", href=True)):
            out[idx] = {"name": nametag.p.text.strip()}
            nxt = get(root + linktag["href"])
            if nxt.status_code != 200:
                print(f"non 200 code for {linktag['href']} {nxt.status_code}")
                return
            nxtSoup = BeautifulSoup(nxt.content, features="html.parser")
            for tag in nxtSoup.find_all("div", attrs={"class":"fullImageLink", "id": "file"}):
                actual_image_link = tag.a["href"]
                r = get(actual_image_link.replace("//", "https://"))
                if r.status_code != 200:
                    print(f"non 200 code for {actual_image_link}")
                    return
                with open(f"gallery/sleeve_{idx}.png", "wb") as f:
                    f.write(r.content)
    # TODO: manually change the names of a few cards...
    with open("sleeve_manifest.json", "w") as f:
        f.write(json.dumps(out, indent=4))

if __name__ == "__main__":
    main()