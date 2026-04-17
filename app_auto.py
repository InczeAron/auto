"""
import os
import time
import re
import smtplib
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

# ide másold:
# - BRANDS
# - COUNTRIES
# - extract_price()

RANDS = {
    "Audi":       ["A1","A2","A3","A4","A5","A6","A7","A8","Q3","Q5","Q7","TT","R8"],
    "BMW":        ["1","2","3","4","5","6","7","X1","X3","X5","Z4","M3","M5"],
    "Mercedes-Benz":   ["A","B","C","E","S","GLA","GLC","GLE","GLK","CLA","CLS","SLK"],
    "Volkswagen": ["Golf","Polo","Passat","Tiguan","Touareg","T-Roc","ID.3","ID.4","Caddy","Sharan"],
    "Ford":       ["Focus","Fiesta","Mondeo","Kuga","Puma","Mustang","Galaxy","S-Max","Transit"],
    "Opel":       ["Astra","Corsa","Insignia","Zafira","Mokka","Crossland","Grandland"],
    "Toyota":     ["Yaris","Corolla","Camry","RAV4","C-HR","Prius","Land Cruiser","Hilux"],
    "Honda":      ["Civic","Jazz","CR-V","HR-V","Accord","FR-V"],
    "Peugeot":    ["107","206","207","208","307","308","407","508","2008","3008","5008"],
    "Renault":    ["Clio","Megane","Laguna","Kangoo","Scenic","Captur","Zoe","Kadjar"],
    "Seat":       ["Ibiza","Leon","Toledo","Altea","Arona","Ateca","Tarraco"],
    "Skoda":      ["Fabia","Octavia","Superb","Kodiaq","Karoq","Rapid","Scala"],
    "Fiat":       ["500","Punto","Bravo","Tipo","Panda","Doblo","Stilo"],
    "Kia":        ["Picanto","Rio","Ceed","Sportage","Sorento","Stonic","Niro","EV6"],
    "Hyundai":    ["i20","i30","i40","Tucson","Santa Fe","Kona","Ioniq"],
    "Mazda":      ["2","3","6","CX-3","CX-5","CX-30","MX-5"],
    "Nissan":     ["Micra","Juke","Qashqai","X-Trail","Leaf","370Z","Navara"],
    "Volvo":      ["S40","S60","S80","V40","V60","V90","XC40","XC60","XC90"],
    "Porsche":    ["911","Cayenne","Macan","Panamera","Taycan","Boxster","Cayman"],
    "Alfa Romeo": ["147","156","159","Giulia","Stelvio","MiTo","Giulietta"],
}

COUNTRIES = {
    "All Europe / Egész Európa":   "",
    "Germany / Németország":       "D",
    "Austria / Ausztria":          "A",
    "Hungary / Magyarország":      "H",
    "Italy / Olaszország":         "I",
    "France / Franciaország":      "F",
    "Spain / Spanyolország":       "E",
    "Belgium":                     "B",
    "Netherlands / Hollandia":     "NL",
    "Poland / Lengyelország":      "PL",
    "Czech Republic / Csehország": "CZ",
    "Switzerland / Svájc":         "CH",
    "Sweden / Svédország":         "S",
    "Denmark / Dánia":             "DK",
    "Portugal / Portugália":       "P",
    "Romania / Románia":           "RO",
    "Croatia / Horvátország":      "HR",
    "Luxembourg / Luxemburg":      "L",
}

def extract_price(text):
    if not text:
        return None

    text = text.replace("\xa0", " ").strip()

    # 🔥 CSAK AZ ELSŐ VALID ÁR FORMÁTUM
    match = re.search(r"\d{1,3}(?:[.,\s]\d{3})+", text)

    if not match:
        return None

    number = match.group(0)

    # minden nem szám törlése
    number = re.sub(r"[^\d]", "", number)

    if not number:
        return None

    value = int(number)

    if 500 < value < 500000:
        return value

    return None

def run_scraper():
    print("SCRAPER FUT")

    cars = []

    # 🔥 IDE MÁSOLD A run_scrape BELSEJÉT
    # DE:
    # ❌ job_id nélkül
    # ❌ jobs dict nélkül
    # ❌ log() nélkül

    def run_scrape():
    brand       = data.get("brand", "")
    model       = data.get("model", "")
    year_from   = data.get("year_from") or None
    year_to     = data.get("year_to") or None
    price_from  = data.get("price_from") or None
    price_to    = data.get("price_to") or None
    country     = COUNTRIES.get(data.get("country", ""), "")
    km_from     = data.get("km_from") or None
    km_to       = data.get("km_to") or None
    seller_type = data.get("seller_type") or None

    #jobs[job_id]["brand"] = brand
    #jobs[job_id]["model"] = model

    brand_slug = brand.lower().replace(" ", "-")
    model_slug = model.lower().replace(" ", "-") 

    # BMW sorozat slug mapping
    BMW_SLUGS = {
        "1": "1-series-(all)",
        "2": "2-series-(all)",
        "3": "3-series-(all)",
        "4": "4-series-(all)",
        "5": "5-series-(all)",
        "6": "6-series-(all)",
        "7": "7-series-(all)",
        "8": "8-series-(all)",
        "x1": "x1", "x2": "x2", "x3": "x3",
        "x4": "x4", "x5": "x5", "x6": "x6", "x7": "x7",
        "z4": "z4", "m3": "m3", "m5": "m5",
    }
    if brand_slug == "bmw" and model.lower() in BMW_SLUGS:
        model_slug = BMW_SLUGS[model.lower()]   

    # Mercedes-Benz model slug fix
    if brand_slug == "mercedes-benz":
        MERCEDES_MODEL_MAP = {
            "a":   "a-class-(all)",
            "b":   "b-class-(all)",
            "c":   "c-class-(all)",
            "e":   "e-class-(all)",
            "s":   "s-class-(all)",
            "gla": "gla-(all)",
            "glc": "glc-(all)",
            "gle": "gle-(all)",
            "glk": "glk-(all)",
            "cla": "cla-(all)",
            "cls": "cls-(all)",
            "slk": "slk-(all)",
        }
        model_slug = MERCEDES_MODEL_MAP.get(model_slug, model_slug)
    cars = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="hu-HU",
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
            page = context.new_page()

            for page_num in range(1, 11):
                params = f"page={page_num}"
                #if model:      params += f"&model={model.upper()}"
                if year_from:  params += f"&fregfrom={year_from}"
                if year_to:    params += f"&fregto={year_to}"
                if price_from: params += f"&pricefrom={price_from}"
                if price_to:   params += f"&priceto={price_to}"
                if country:    params += f"&cy={country}"
                if km_from:     params += f"&kmfrom={km_from}"
                if km_to:       params += f"&kmto={km_to}"
                if seller_type == "dealer":
                    params += "&atype=C&adtype=D"
                elif seller_type == "private":
                    params += "&atype=C&adtype=P"
                if year_from or year_to:
                    params += "&sort=age&desc=1"
                elif price_from or price_to:
                    params += "&sort=price&desc=0"

                url = f"https://www.autoscout24.com/lst/{brand_slug}/{model_slug}?{params}"
                log(job_id, f"📄 Loading page / Oldal betöltése: {page_num}")
                page.goto(url, wait_until="domcontentloaded", timeout=30000)

                try:
                    page.wait_for_selector("article", timeout=8000)
                except:
                    page.wait_for_selector("[data-testid='listing']", timeout=8000)

                # 🔥 görgetés, hogy betöltse az összes hirdetést
                page.mouse.wheel(0, 3000)
                time.sleep(1)
                page.mouse.wheel(0, 3000)
                time.sleep(1)

                articles = page.locator("article").all()

                if not articles:
                    articles = page.locator("[data-testid='listing']").all()

                log(job_id, f"Találatok: {len(articles)}")

                if page_num == 1:
                    for selector in ["button[id='didomi-notice-agree-button']",
                                     "button:has-text('Accept All')", "button:has-text('Accept all')"]:
                        try:
                            btn = page.locator(selector).first
                            if btn.is_visible(timeout=2000):
                                btn.click()
                                log(job_id, "✅ Cookie accepted / Cookie elfogadva")
                                time.sleep(1)
                                break
                        except Exception:
                            continue

                try:
                    page.wait_for_selector("a[href*='/offers/']", timeout=10000)
                except Exception:
                    time.sleep(3)

                

                # 🔥 fallback (új UI miatt)
                if not articles:
                    articles = page.locator("[data-testid='listing']").all()

                    log(job_id, f"  → {len(articles)} listings / hirdetés")

                    print("HTML length:", len(page.content()))

                if not articles:
                    log(job_id, "⛔ No more results / Nincs több találat")
                    break

                log(job_id, f"  → {len(articles)} listings / hirdetés")

                for article in articles:
                    try:
                        title = ""
                        try:
                            title = article.locator("h2").first.inner_text(timeout=1000).strip()
                        except Exception:
                            pass

                        price_num = None
                        price_text = ""

                        try:
                            price_text = article.locator("[class*='Price'], [class*='price']").first.inner_text(timeout=1000).strip()

                            # 🔥 LEVÁGJUK A VÉGÉRŐL A NEM SZÁM KARAKTEREKET (pl. ¹)
                            price_text = re.sub(r"[^\d€.,\s]", "", price_text)

                            price_num = extract_price(price_text)

                        except Exception:
                            pass

                        details = []
                        try:
                            spans = article.locator("dl span, [class*='VehicleDetails'] span, [class*='vehicle-detail'] span").all()
                            for s in spans[:6]:
                                t = s.inner_text(timeout=500).strip()
                                if t and t not in details:
                                    details.append(t)
                        except Exception:
                            pass

                        location = ""
                        for loc_sel in ["[data-testid='seller-address']","[data-testid='location']",
                                        "[class*='seller-address']","[class*='sellerAddress']","address",
                                        "[class*='Location']","[class*='location']","[class*='seller']"]:
                            try:
                                el = article.locator(loc_sel).first
                                if el.is_visible(timeout=500):
                                    txt = el.inner_text(timeout=500).strip()
                                    if txt and len(txt) > 2:
                                        location = txt
                                        break
                            except Exception:
                                continue
                        if not location:
                            try:
                                full_text = article.inner_text(timeout=1000)
                                match = re.search(r'\b([A-Z]{1,3}-\s*\d{4,5}[\s\S]{0,30})', full_text)
                                if match:
                                    location = match.group(1).split('\n')[0].strip()
                            except Exception:
                                pass

                        link = ""

                        try:
                            # 🔥 KÉPRE KATTINTÁS (legstabilabb módszer)
                            img_link = article.locator("a:has(img)").first

                            if img_link.count() > 0:
                                href = img_link.get_attribute("href")

                                if href:
                                    if href.startswith("/"):
                                        link = "https://www.autoscout24.com" + href
                                    else:
                                        link = href

                        except Exception:
                            pass

                        # 🔥 fallback (ha kép nem működik)
                        if not link:
                            try:
                                href = article.locator("a[href*='/offers/']").first.get_attribute("href")
                                if href:
                                    if href.startswith("/"):
                                        link = "https://www.autoscout24.com" + href
                                    else:
                                        link = href
                            except:
                                pass

                        # 🔥 tracking levágása
                        if link:
                            link = link.split("?")[0]

                        # Eladó típusának kiolvasása az article HTML-ből
                        seller_label = ""
                        try:
                            full_text = article.inner_text(timeout=1000)
                            full_html = article.inner_html(timeout=1000)
                            
                            # Debug: első article szövegének kiírása
                            #if len(cars) == 0:
                                #print("=== ARTICLE TEXT SAMPLE ===")
                                #print(full_text[:500])
                                #print("=== ARTICLE HTML SAMPLE ===")
                                #print(full_html[:800])
                                #print("===========================")                                             
                            # Seller típus keresése szövegben és HTML-ben
                            combined = full_text + full_html
                            combined_lower = combined.lower()
                            if any(x in combined_lower for x in ["private seller", "privateseller", "private-seller",
                                                                  "privatanbieter", "private_seller",
                                                                  "seller-private", "adtypeprivate"]):
                                seller_label = "private"
                            elif any(x in combined_lower for x in ["dealer", "händler",
                                                                    "adtypedealer", "seller-dealer"]):
                                seller_label = "dealer"
                        except Exception as e:
                            print(f"Seller detect error: {e}")
                            pass

                        # Szűrés eladó típusa alapján
                        if seller_type == "private" and seller_label == "dealer":
                            continue
                        if seller_type == "dealer" and seller_label == "private":
                            continue

                        if title:
                            # 🔥 MODEL SZŰRÉS (pl. GLA csak önálló szóként)
                            if model:
                                model_clean = model.lower().strip()
                                title_clean = title.lower().strip()

                                # 🔥 MERCEDES
                                if brand.lower() == "mercedes-benz":
                                    if not re.search(rf"\b{re.escape(model_clean)}\s?\d+", title_clean):
                                        continue

                                # 🔥 BMW (javítás) URL már szűr sorozatra
                                elif brand.lower() == "bmw":
                                    pass
                            # Ár megjelenítése: szám → formázott string                                       
                            price_display = f"{price_num:,} €".replace(",", ".") if price_num else price_text
                            cars.append({
                                "Cím":     title,
                                "Ár":      price_display,
                                "Ár_num":  price_num,
                                "Részletek": " | ".join(details),
                                "Helyszín": location,
                                "Link":    link
                            })
                    except Exception:
                        continue

                jobs[job_id]["progress"] = page_num * 10

            browser.close()

        cars.sort(key=lambda x: x["Ár_num"] if x["Ár_num"] else 999999)
        jobs[job_id]["cars"] = cars
        jobs[job_id]["status"] = "done"
        log(job_id, f"🎉 Done! / Kész! {len(cars)} listings / hirdetés collected.")

    except Exception as e:
        log(job_id, f"⚠️ Hiba, de megyünk tovább: {e}")
        # Ha már vannak összegyűjtött autók, azokat mentsük el
        if cars:
            cars.sort(key=lambda x: x["Ár_num"] if x["Ár_num"] else 999999)
            jobs[job_id]["cars"] = cars
            jobs[job_id]["status"] = "done"
            log(job_id, f"🎉 Részleges eredmény / Partial result: {len(cars)} listings / hirdetés.")
        else:
            jobs[job_id]["status"] = "error"
            log(job_id, "❌ Nincs eredmény / No results collected.")                         


    return cars


def format_email(cars):
    if not cars:
        return "Nincs találat"

    top = cars[:5]

    text = "🔥 TOP DEALS:\n\n"
    for c in top:
        text += f"{c['Cím']}\n{c['Ár']}\n{c['Link']}\n\n"

    return text


def send_email(content):
    EMAIL = os.getenv("EMAIL_USER")
    PASSWORD = os.getenv("EMAIL_PASS")

    msg = MIMEText(content)
    msg["Subject"] = "🚗 Auto Deals"
    msg["From"] = EMAIL
    msg["To"] = EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, PASSWORD)
        server.send_message(msg)

    print("EMAIL ELKÜLDVE")


if __name__ == "__main__":
    cars = run_scraper()
    content = format_email(cars)
    send_email(content)"""

#--------------------------------------------- github scrapper ------------------------------------------
import time, re
from playwright.sync_api import sync_playwright
from openpyxl import Workbook

def extract_price(text):
    if not text:
        return None
    text = text.replace("\xa0", " ").strip()
    match = re.search(r"\d{1,3}(?:[.,\s]\d{3})+", text)
    if not match:
        return None
    number = re.sub(r"[^\d]", "", match.group(0))
    if not number:
        return None
    value = int(number)
    return value if 500 < value < 500000 else None


def run_scraper():
    print("SCRAPER FUT")

    # 👉 IDE ÍRD BE FIXEN amit keresel (később paraméterezheted)
    brand = "bmw"
    model = "3"
    year_from = 2020
    year_to = 2024
    price_from = None
    price_to = None
    country = "D"

    brand_slug = brand.lower()
    model_slug = "3-series-(all)"

    cars = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for page_num in range(1, 3):  # teszthez elég 2 oldal
            params = f"page={page_num}&fregfrom={year_from}&fregto={year_to}&cy={country}"
            url = f"https://www.autoscout24.com/lst/{brand_slug}/{model_slug}?{params}"

            print("URL:", url)

            page.goto(url, timeout=30000)

            try:
                page.wait_for_selector("article", timeout=8000)
            except:
                print("Nincs találat")
                continue

            articles = page.locator("article").all()

            print("Találatok:", len(articles))

            for article in articles:
                try:
                    title = article.locator("h2").first.inner_text(timeout=1000).strip()

                    price_text = article.locator("[class*='Price']").first.inner_text(timeout=1000)
                    price_num = extract_price(price_text)

                    link = article.locator("a[href*='/offers/']").first.get_attribute("href")
                    if link and link.startswith("/"):
                        link = "https://www.autoscout24.com" + link

                    cars.append({
                        "Cím": title,
                        "Ár": price_text,
                        "Ár_num": price_num,
                        "Link": link
                    })

                except:
                    continue
                

        browser.close()

    cars.sort(key=lambda x: x["Ár_num"] if x["Ár_num"] else 999999)

    # 📊 Excel mentés
    wb = Workbook()
    ws = wb.active
    ws.title = "Autos"

    # fejléc
    ws.append(["Cím", "Ár", "Ár_num", "Link"])

    # adatok
    for car in cars:
        ws.append([
            car["Cím"],
            car["Ár"],
            car["Ár_num"],
            car["Link"]
        ])

    # mentés
    filename = "autoscout_results_2020-24_bmww3_DE.xlsx"
    wb.save(filename)

    print(f"Excel mentve: {filename}")

    print(f"Talált autók: {len(cars)}")

    for car in cars[:10]:
        print(car)

    return cars