import time, re, smtplib, os, psycopg2
from playwright.sync_api import sync_playwright
from email.message import EmailMessage


# =========================
# DATABASE
# =========================
def parse_date(date_str):
    try:
        month, year = date_str.split("/")
        return int(year), int(month)
    except:
        return (0, 0)

def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"), sslmode="require")

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_cars (
            id SERIAL PRIMARY KEY,
            dealer_id TEXT,
            car_id TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def load_seen(dealer_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT car_id FROM sent_cars WHERE dealer_id = %s", (dealer_id,))
    seen = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return seen

def save_seen(dealer_id, car_ids):
    if not car_ids:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    for car_id in car_ids:
        cur.execute(
            "INSERT INTO sent_cars (dealer_id, car_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (dealer_id, car_id)
        )
    conn.commit()
    cur.close()
    conn.close()


# =========================
# EMAIL
# =========================
def send_email(subject, body, to_email, attachment=None, html=False):
    sender = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender

    # to_email lehet string vagy lista
    if isinstance(to_email, list):
        msg["To"] = ", ".join(to_email)
    else:
        msg["To"] = to_email

    if html:
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    if attachment and os.path.exists(attachment):
        with open(attachment, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=os.path.basename(attachment)
            )

    """with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)"""
    
    with smtplib.SMTP_SSL("smtp.forpsi.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(msg)

    print(f"📧 Email elküldve: {msg['To']}")


# =========================
# EXCEL
# =========================
def save_to_excel(cars, filename):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = Workbook()
    ws = wb.active
    ws.title = "AutoScout"

    headers = ["#", "Title", "Price", "Mileage", "Year", "Fuel", "Location", "Link", "Deal"]
    header_fill = PatternFill(start_color="2F4F6F", end_color="2F4F6F", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    for car in cars:
        rating = car.get("Pontszám") or 0
        deal_text = f"{abs(rating)}% cheaper" if rating > 0 else f"{abs(rating)}% more expensive"
        color = "008000" if rating > 0 else "FF0000"

        ws.append([
            car.get("Sorszám"),
            car.get("Cím"),
            car.get("Ár"),
            car.get("Km") or "-",
            car.get("Év") or "-",
            car.get("Üzemanyag") or "-",
            car.get("Helyszín") or "-",
            "Open",
            deal_text
        ])

        row = ws.max_row
        link_cell = ws.cell(row=row, column=8)
        link_cell.hyperlink = car.get("Link") or ""
        link_cell.font = Font(color="0000FF", underline="single")

        deal_cell = ws.cell(row=row, column=9)
        deal_cell.font = Font(color=color, bold=True)

        link = car.get("Link")
        print("LINK:", link)

        car_id = link.rstrip("/").split("/")[-1]
        print("CAR_ID:", car_id)

    widths = [5, 50, 15, 12, 12, 12, 20, 8, 15]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w

    wb.save(filename)
    print(f"✅ Excel mentve: {filename}")


# =========================
# HTML EMAIL
# =========================
def build_email_html(cars, medians, search_label=""):
    html = f"""
    <html><body>
    <h2>🚗 New cars – {search_label}</h2>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;font-family:Arial;">
        <tr style="background-color:#2f4f6f;color:white;">
            <th>#</th><th>Title</th><th>Price</th><th>Mileage</th><th>Year</th><th>Location</th><th>Link</th><th>Deal</th>
        </tr>
    """
    for car in cars:
        rating = car.get("Pontszám") or 0
        color = "green" if rating > 0 else "red"
        text = f"{abs(rating)}% cheaper" if rating > 0 else f"{abs(rating)}% more expensive"
        html += f"""
        <tr>
            <td>{car.get("Sorszám")}</td>
            <td>{car.get("Cím")}</td>
            <td>{car.get("Ár")}</td>
            <td>{car.get("Km") or '-'}</td>
            <td>{car.get("Év") or '-'}</td>
            <td>{car.get("Helyszín") or '-'}</td>
            <td><a href="{car.get("Link")}">Open</a></td>
            <td style="color:{color};font-weight:bold;">{text}</td>
        </tr>"""
    html += "</table>"
    
     # 🔥 MEDIÁN RÉSZ
    if medians:
        html += "<br><h3>📊 Median prices by year</h3><ul>"
        for year, median in sorted(medians.items(), reverse=True):
            html += f"<li>{year}: {int(median):,} €</li>".replace(",", ".")
        html += "</ul>"

    html += "</body></html>"

    return html


# =========================
# PRICE EXTRACT
# =========================
def extract_price(text):
    if not text:
        return None
    text = text.replace("\xa0", " ").strip()
    match = re.search(r"\d{1,3}(?:[.,\s]\d{3})+", text)
    if not match:
        match = re.search(r"\d+", text)
    if not match:
        return None
    value = int(re.sub(r"[^\d]", "", match.group(0)))
    return value if 500 < value < 500000 else None


# =========================
# SCRAPE ONE SEARCH
# =========================
def scrape_search(page, brand, model_slug, year_from, year_to, country):
    cars = []

    for page_num in range(1, 10):
        print(f"  📄 Oldal: {page_num}")
        url = (f"https://www.autoscout24.com/lst/{brand}/{model_slug}"
               f"?page={page_num}&fregfrom={year_from}&fregto={year_to}&cy={country}")

        try:
            page.goto(url, timeout=25000)
        except Exception:
            print("  ❌ Oldal nem tölt be")
            break

        html_len = len(page.content())
        if html_len < 5000:
            print("  ⛔ Valószínű CAPTCHA/block")
            break

        # Cookie
        try:
            btn = page.locator("button:has-text('Accept')").first
            if btn.is_visible(timeout=2000):
                btn.click()
        except Exception:
            pass

        try:
            page.wait_for_selector("article", timeout=5000)
        except Exception:
            pass

        print("URL:", page.url)
        print("HTML LEN:", len(page.content()))

        articles = page.locator("article").all()

        print("Összes href az első article-ben:")

        for a in articles[0].locator("a").all():
            print(a.get_attribute("href"))

        print("ARTICLE COUNT:", len(articles))

        if len(articles) == 0:
            page.screenshot(path="debug.png")
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(page.content())

        print("URL:", page.url)

        html = page.content()

        print("HTML SIZE:", len(html))

        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(html)

        page.screenshot(path="debug.png")

        articles = page.locator("article").all()
        if not articles:
            print("  ⛔ Nincs találat")
            break

        print(f"  → {len(articles)} hirdetés")

        for article in articles:
            try:
                title = article.locator("h2").first.inner_text(timeout=1000).strip()
                price_text = article.locator("[class*='Price']").first.inner_text(timeout=1000).strip()
                price_num = extract_price(price_text)

                link = ""
                try:
                    href = article.locator("a[href*='/offers/']").first.get_attribute("href", timeout=500)
                    if href:
                        link = "https://www.autoscout24.com" + href if href.startswith("/") else href
                        link = link.split("?")[0]
                except Exception:
                    pass

                km = None
                year = ""
                fuel = ""
                location = ""

                try:
                    spans = article.locator("span").all()
                    for d in spans:
                        txt = d.inner_text(timeout=300).strip().lower()
                        if "km" in txt and re.search(r"\d", txt):
                            km_str = re.sub(r"[^\d]", "", txt)
                            km = int(km_str) if km_str else None
                        elif re.search(r"\d{2}/\d{4}", txt):
                            year = txt
                        elif any(f in txt for f in ["diesel", "benzin", "gasoline", "petrol", "electric", "hybrid"]):
                            fuel = txt
                except Exception:
                    pass

                try:
                    spans = article.locator("span").all()
                    for s in spans:
                        txt = s.inner_text(timeout=200).strip()

                        # pl: "DE-12345 Berlin"
                        if re.search(r"[A-Z]{2}-\d{4,5}", txt):
                            location = txt
                            break
                except:
                    location = ""

                cars.append({
                    "Sorszám": len(cars) + 1,
                    "Cím":     title,
                    "Ár":      f"{price_num:,} €".replace(",", ".") if price_num else price_text,
                    "Ár_num":  price_num,
                    "Km":      km,
                    "Év":      year,
                    "Üzemanyag": fuel,
                    "Helyszín":  location,
                    "Link":    link,
                    "Pontszám": 0
                })

            except Exception:
                continue

        time.sleep(2)

    return cars


# =========================
# MAIN alap
# =========================
def run_scraper():
    print("🚀 SCRAPER START")
    init_db()

    dealers = [
        {
            "dealer_id": "dealer1",
            "emails": ["aronincze@aronsoft.hu"],
            "searches": [
                {"brand": "bmw",   "model": "3-series-(all)", "year_from": 2024, "year_to": 2026, "country": "D"},
            ]
        },
        {
            "dealer_id": "dealer1",
            "emails": ["aronincze@aronsoft.hu"],
            "searches": [
                {"brand": "audi", "model": "a6", "year_from": 2024, "year_to": 2026, "country": "A"},
            ]
        },
        {
            "dealer_id": "dealer2",
            "emails": ["inczearon@gmail.com"],
            "searches": [
                {"brand": "mercedes-benz", "model": "gla-(all)", "year_from": 2024, "year_to": 2026, "country": "D"},
            ]
        },
        {
            "dealer_id": "dealer2",
            "emails": ["inczearon@gmail.com"],
            "searches": [
                {"brand": "volkswagen", "model": "golf", "year_from": 2024, "year_to": 2026, "country": "D"},
            ]
        },
    ]

    from playwright.sync_api import sync_playwright
    import random

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119 Safari/537.36",
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-sandbox", "--disable-dev-shm-usage"]
        )

        all_medians = {}

        for dealer in dealers:
            dealer_id = dealer["dealer_id"]
            emails    = dealer["emails"]

            print(f"\n{'='*40}")
            print(f"🏢 Dealer: {dealer_id}")

            # 🔥 ÚJ CONTEXT DEALERENKÉNT
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 800},
                locale="de-DE"
            )

            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )

            seen = load_seen(dealer_id)

            all_new_cars = []
            all_new_ids  = []

            for search in dealer["searches"]:
                label = f"{search['brand']} {search['model']} ({search['country']})"
                print(f"\n🔍 Keresés: {label}")

                page = context.new_page()

                cars = scrape_search(
                    page,
                    search["brand"],
                    search["model"],
                    search["year_from"],
                    search["year_to"],
                    search["country"]
                )

                page.close()

                print(f"  🎯 Összesen: {len(cars)} autó")

                if len(cars) == 0:
                    print("  ⚠️ NINCS TALÁLAT (block vagy selector hiba)")

                # Átlag + pontszám
                """valid_prices = [c["Ár_num"] for c in cars if c.get("Ár_num")]
                avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0

                for c in cars:
                    if c.get("Ár_num") and avg_price:
                        c["Pontszám"] = round((avg_price - c["Ár_num"]) / avg_price * 100)
                        c["Átlag"] = avg_price   # 🔥 új"""
                
                #csoportosítás év szerint
                cars_by_year = {}

                for c in cars:
                    year = c.get("Év")
                    price = c.get("Ár_num")

                    if not year or not price:
                        continue

                    # pl: "03/2024" → "2024"
                    year_only = year.split("/")[-1]

                    if year_only not in cars_by_year:
                        cars_by_year[year_only] = []

                    cars_by_year[year_only].append(price)

                #medián számítás évente
                medians = {}

                for year, prices in cars_by_year.items():
                    prices = sorted(prices)
                    n = len(prices)

                    if n == 0:
                        continue

                    if n % 2 == 1:
                        median = prices[n // 2]
                    else:
                        median = (prices[n//2 - 1] + prices[n//2]) / 2

                    medians[year] = median

                    all_medians.update(medians)

                #pontszám számítás (évente)
                for c in cars:
                    year = c.get("Év")
                    price = c.get("Ár_num")

                    if not year or not price:
                        continue

                    year_only = year.split("/")[-1]
                    median = medians.get(year_only)

                    if median:
                        c["Pontszám"] = round((median - price) / median * 100)
                        c["Medián"] = median  # extra debug/info  

                # Új autók szűrése
                for car in cars:
                    link = car.get("Link")
                    print("LINK:", link)
                    if not link:
                        continue

                    car_id = link.rstrip("/").split("/")[-1]
                    print("CAR_ID:", car_id)

                    print("SEEN:", car_id in seen)

                    if not car_id or len(car_id) < 10:
                        print("SKIP: short id")
                        continue

                    if car_id not in seen:
                        seen.add(car_id)  # 🔥 KRITIKUS FIX
                        car["Keresés"] = label
                        all_new_cars.append(car)
                        all_new_ids.append(car_id)

            context.close()  # 🔥 FONTOS

            print(f"\n📬 New cars ({dealer_id}): {len(all_new_cars)}")

            # 🔥 MINDIG MENTSD EL AZ ÚJ ID-KAT!
            save_seen(dealer_id, all_new_ids)

            if not all_new_cars:
                send_email(
                    subject=f"🚗 AutoScout – {dealer_id} – nincs új autó / no new car",
                    body="...",
                    to_email=emails
                )
                continue

            # Rendezés
            all_new_cars.sort(
                key=lambda x: (
                    parse_date(x.get("Év")),          # 1️⃣ év+hónap
                    x.get("Pontszám") or -999         # 2️⃣ deal
                ),
                reverse=True
            )

            # Sorszám újra
            for i, c in enumerate(all_new_cars, 1):
                c["Sorszám"] = i

            # Excel
            filename = f"{dealer_id}_{search['brand']}.xlsx" #f"{dealer_id}.xlsx"
            save_to_excel(all_new_cars, filename)

            # DB mentés
            save_seen(dealer_id, all_new_ids)

            # Email
            email_html = build_email_html(all_new_cars, all_medians, dealer_id)

            send_email(
                subject=f"🚗 {len(all_new_cars)} új autó – {dealer_id}",
                body=email_html,
                to_email=emails,
                html=True,
                attachment=filename
            )

        browser.close()

    print("\n✅ SCRAPER KÉSZ")


if __name__ == "__main__":
    try:
        run_scraper()
    except Exception as e:
        import traceback
        send_email(
            subject="❌ SCRAPER HIBA",
            body=traceback.format_exc(),
            to_email="aronincze@aronsoft.hu"
        )
