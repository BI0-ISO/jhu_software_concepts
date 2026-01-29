import mechanicalsoup

browser = mechanicalsoup.Browser()

url = "http://olympus.realpython.org/login"
page = browser.get(url)

print(page)

print(type(page.soup))

print(page.soup)