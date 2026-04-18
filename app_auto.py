
    #----------------------------- új verzió tisztán chat gpt-től --------------------

import time, re, smtplib, os
from playwright.sync_api import sync_playwright
from openpyxl import Workbook
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject, body, to_email, attachment=None):
    sender = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    # Excel csatolmány
    if attachment:
        with open(attachment, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=attachment
            )

    # Gmail SMTP
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)

    print(f"📧 Email elküldve: {to_email}")


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


def save_to_excel(cars, filename):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active

    # ✅ fejléc
    ws.append(["#", "Cím", "Ár", "Km", "Év", "Üzemanyag", "Helyszín", "Link", "Pontszám"])

    for car in cars:
        ws.append([
            car.get("Sorszám"),
            car.get("Cím"),
            car.get("Ár"),
            car.get("Km"),
            car.get("Év"),
            car.get("Üzemanyag"),
            car.get("Helyszín"),
            "Open",
            car.get("Pontszám")
        ])

        # ✅ kattintható link
        row = ws.max_row
        ws.cell(row=row, column=8).hyperlink = car.get("Link")

    wb.save(filename)
    print(f"Excel mentve: {filename}")

def build_email_text(cars):
    text = "TOP autók:\n\n"

    for car in cars[:10]:
        text += f"{car['Sorszám']}. {car['Cím']}\n"
        text += f"Ár: {car['Ár']}\n"
        text += f"Link: {car['Link']}\n"
        text += f"Pontszám: {car['Pontszám']}%\n"
        text += "-" * 30 + "\n"

    return text  

def send_email(subject, body, to_email, attachment=None):
    sender = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    # Excel csatolmány
    if attachment:
        with open(attachment, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=attachment
            )

    # Gmail SMTP
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(sender, password)
        smtp.send_message(msg)

    print(f"📧 Email elküldve: {to_email}")

def run_scraper():
    print("🚀 SCRAPER START")

    brand = "bmw"
    model_slug = "3-series-(all)"
    year_from = 2024
    year_to = 2026
    country = "D"

    cars = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="de-DE"
        )

        # 🔥 stealth hack
        context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = context.new_page()

        for page_num in range(1, 4):  # max 3 oldal
            print(f"\n📄 OLDAL: {page_num}")

            url = f"https://www.autoscout24.com/lst/{brand}/{model_slug}?page={page_num}&fregfrom={year_from}&fregto={year_to}&cy={country}"

            try:
                page.goto(url, timeout=20000)
            except:
                print("❌ Nem tölt be az oldal")
                break

            # DEBUG
            html_len = len(page.content())
            print("HTML méret:", html_len)

            if html_len < 5000:
                print("⛔ VALÓSZÍNŰ BLOCK / CAPTCHA")
                page.screenshot(path=f"debug_block_{page_num}.png")
                break

            # cookie accept
            try:
                btn = page.locator("button:has-text('Accept')").first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    print("✅ Cookie OK")
            except:
                pass

            try:
                page.wait_for_selector("article", timeout=5000)
            except:
                print("⚠️ Nincs article → fallback")

            articles = page.locator("article").all()

            if not articles:
                print("⛔ NINCS TALÁLAT → STOP")
                break

            print("Találatok:", len(articles))

            for i, article in enumerate(articles):
                if i > 30:  # limit
                    break

                year = ""
                fuel = ""
                location = ""
                rating = 0
                km = None

                try:
                    title = article.locator("h2").first.inner_text(timeout=1000)

                    price_text = article.locator("[class*='Price']").first.inner_text(timeout=1000)
                    price_num = extract_price(price_text)

                    link = article.locator("a[href*='/offers/']").first.get_attribute("href")
                    if link and link.startswith("/"):
                        link = "https://www.autoscout24.com" + link

                    cars.append({
                        "Sorszám": len(cars) + 1,
                        "Cím": title,
                        "Ár": f"{price_num:,} €".replace(",", ".") if price_num else price_text,
                        "Ár_num": price_num,
                        "Km": km,
                        "Év": year,
                        "Üzemanyag": fuel,
                        "Helyszín": location,
                        "Link": link,
                        "Pontszám": rating
                    })

                    if not price_num:
                        continue

                    details = article.locator("span").all()

                    for d in details:
                        txt = d.inner_text(timeout=500).strip().lower()

                        if "km" in txt:
                            km = re.sub(r"[^\d]", "", txt)
                            cars[-1]["km"] = int(km) if km else None

                        elif re.search(r"\d{2}/\d{4}", txt):
                            cars[-1]["year"] = txt

                        elif "diesel" in txt or "benzin" in txt or "gasoline" in txt:
                            cars[-1]["fuel"] = txt

                except:
                    continue

            time.sleep(2)  # 🔥 ne pörögjön túl gyorsan

        browser.close()

        # 🔥 Átlag ár számítás
        valid_prices = [c["Ár_num"] for c in cars if c.get("Ár_num")]
        avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0

        # 🔥 Pontszám számítás
        for c in cars:
            if c.get("Ár_num") and avg_price:
                diff = (avg_price - c["Ár_num"]) / avg_price * 100
                c["Pontszám"] = round(diff)
            else:
                c["Pontszám"] = None

    # rendezés
    cars.sort(key=lambda x: x.get("price") or 999999)

    print(f"\n🎯 Talált autók: {len(cars)}")

    for car in cars[:5]:
        print(car)

    # 🔥 Excel mentés
    filename = "autoscout_results_2020-24_bmw3_DE.xlsx"
    save_to_excel(cars, filename)

    # email szöveg
    email_text = build_email_text(cars)

    # saját email (excel + lista)
    send_email(
        subject="🚗 AutoScout lista",
        body=email_text,
        to_email="aronincze@aronsoft.hu",
        attachment=filename
    )

    # ügyfél email (csak lista)
    client_email = "inczearon@gmail.com"  # ide írd
    send_email(
        subject="🚗 Ajánlott autók",
        body=email_text,
        to_email=client_email
    )

    try:
        run_scraper()
    except Exception as e:
        send_email(
            subject="❌ SCRAPER HIBA",
            body=str(e),
            to_email="aronincze@aronsoft.hu"
        )
        raise


if __name__ == "__main__":
    run_scraper()