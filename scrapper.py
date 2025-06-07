# Optional: Convert to JSON string (for API or storage)
import json
import requests
from bs4 import BeautifulSoup

chai_doc_collection="chai_doc_documents"

async def get_html(path:str):
    # url = 'https://chaidocs.vercel.app/youtube/getting-started/'
    url = path

    response = requests.get(url)
    if response.status_code != 200:
        print(url)
        raise Exception('Network response was not ok')

    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    return soup

async def get_content(path:str):
    url=f"https://chaidocs.vercel.app/youtube/{path}"
    print(url)
    soup=await get_html(url)

    contents = soup.find_all("main")
    print(contents)
    text_data=""
    for content in contents:
        text_data += content.get_text(separator=" ",strip=True)
        # print(content.get_text(strip=True))
    return text_data

async def get_paths():
    soup=await get_html('https://chaidocs.vercel.app/youtube/getting-started/')
    elements = soup.find_all(class_='top-level')
    print(elements)
    hrefs = []
    for element in elements:
        links = element.find_all('a')
        for link in links:
            href = link.get('href')
            if href:  # check if href exists
                hrefs.append(href.replace("youtube/",""))

    # print all href values
    for href in hrefs:
        print(href)  # ya .text agar sirf text chahiy

    result = {}
    for link in hrefs:
        parts = link.strip("/").split("/")
        if len(parts) == 1:
            section = parts[0]
            if section not in result:
                result[section] = {
                    "name": section,
                    "paths": ["/"]
                }
        elif len(parts) > 1:
            section = parts[0]
            subpath = "/".join(parts[1:])
            if section not in result:
                result[section] = {
                    "name": section,
                    "paths": []
                }
            result[section]["paths"].append(subpath)
    return result

