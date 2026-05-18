import time
from datetime import datetime, timedelta
import requests
from ryanair import Ryanair
from dateutil import parser

# ==================== NUSTATYMAI ====================
TELEGRAM_TOKEN = "8859931956:AAEe-eRgpc1aOM9wSSbvSczdSh7PLyi0q4I"
TELEGRAM_CHAT_ID = "8537537381"

ORIGIN_AIRPORTS = ["VNO", "KUN"]
MAX_TOTAL_PRICE = 100  # Standartinėms kelionėms į abi puses
MAX_TRIANGLE_PRICE = 130 # Maksimali kaina VISIEMS 3 TRŪKSTAMIEMS SKRYDŽIAMS kartu sudėjus
CURRENCY = "EUR"

# TOP oro uostų kodai pagal tavo pasirinktas šalis (Italija, Ispanija, Prancūzija, Kroatija, Austrija)
TOP_DESTINATIONS = [
    "CIA", "FCO", "BGY", "MXP", "VCE", "TSF", "BRI", "BLQ", "NAP", "PSA", "TRN", "PSR", # Italija
    "BCN", "MAD", "ALC", "PMI", "AGP", "VLC", # Ispanija
    "BVA", "NCE", # Prancūzija
    "ZAD", "SPU", "ZAG", # Kroatija
    "VIE" # Austrija
]
# ====================================================

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Klaida siunčiant žinutę: {e}")

def format_time(dt_str):
    dt = parser.parse(str(dt_str))
    return dt, dt.strftime("%Y-%m-%d %H:%M")

def search_italy_triangle(api, tomorrow, search_end):
    """Speciali funkcija tavo Italijos trikampio maršrutui"""
    print("\n🔎 Vykdau specifinę KUN -> BRI -> VCE/TSF -> BGY/TSF -> VNO paiešką...")
    try:
        kun_bri = api.get_cheapest_flights("KUN", tomorrow, search_end)
        kun_to_bri = [f for f in kun_bri if f.destination == "BRI"]

        bri_flights = api.get_cheapest_flights("BRI", tomorrow, search_end + timedelta(days=10))
        bri_to_venice = [f for f in bri_flights if f.destination in ["VCE", "TSF"]]

        tsf_vno = api.get_cheapest_flights("TSF", tomorrow, search_end + timedelta(days=15))
        bgy_vno = api.get_cheapest_flights("BGY", tomorrow, search_end + timedelta(days=15))
        back_to_vno = [f for f in tsf_vno if f.destination == "VNO"] + [f for f in bgy_vno if f.destination == "VNO"]

        for f1 in kun_to_bri:
            d1, t1 = format_time(f1.departureTime)
            if d1.hour >= 19: continue

            for f2 in bri_to_venice:
                d2, t2 = format_time(f2.departureTime)
                if 1 <= (d2.date() - d1.date()).days <= 3:

                    for f3 in back_to_vno:
                        d3, t3 = format_time(f3.departureTime)
                        if d3.hour < 9: continue

                        total_days = (d3.date() - d1.date()).days
                        next_stay = (d3.date() - d2.date()).days

                        if 3 <= total_days <= 7 and 1 <= next_stay <= 3:
                            total_cost = f1.price + f2.price + f3.price

                            if total_cost <= MAX_TRIANGLE_PRICE:
                                msg = (
                                    f"🍕 🎭 *RADAU ITALIJOS TRIKAMPĮ! (3 skrydžiai)*\n\n"
                                    f"💰 *Bendra kaina už VISKĄ:* *{total_cost:.2f}€*\n"
                                    f"📅 *Bendra trukmė:* {total_days} d.\n\n"
                                    f"1️⃣ 🛫 *KUN -> BRI:* {t1} ({f1.price:.2f}€)\n"
                                    f"2️⃣ ✈️ *BRI -> {f2.destination}:* {t2} ({f2.price:.2f}€)\n"
                                    f"3️⃣ 🛬 *{f3.origin} -> VNO:* {t3} ({f3.price:.2f}€)"
                                )
                                print(f"🔥 RASTAS TRIKAMPIS: KUN->BRI->{f2.destination}->VNO už {total_cost:.2f}€")
                                send_telegram_message(msg)
                                time.sleep(2)
    except Exception as e:
        print(f"Klaida Italijos trikampio paieškoje: {e}")

def search_standard_flights(api, tomorrow, search_end):
    """Tavo standartinė paieška į abi puses"""
    print("\n🔎 Vykdau standartinę skrydžių paiešką...")
    for origin in ORIGIN_AIRPORTS:
        try:
            outbound_flights = api.get_cheapest_flights(origin, tomorrow, search_end)
            destinations = set([f.destination for f in outbound_flights])

            for dest in destinations:
                to_dest = [f for f in outbound_flights if f.destination == dest]
                try:
                    inbound_flights = api.get_cheapest_flights(dest, tomorrow, search_end + timedelta(days=15))
                    from_dest = [f for f in inbound_flights if f.destination == origin]
                except: continue

                for out_f in to_dest:
                    out_datetime, out_time_clean = format_time(out_f.departureTime)
                    if out_datetime.hour >= 19: continue

                    for in_f in from_dest:
                        in_datetime, in_time_clean = format_time(in_f.departureTime)
                        if in_datetime.hour < 9: continue

                        stay_duration = (in_datetime.date() - out_datetime.date()).days
                        if 2 <= stay_duration <= 14:
                            total_price = out_f.price + in_f.price
                            if total_price <= MAX_TOTAL_PRICE:
                                # Tikriname ar oro uosto kodas yra mūsų TOP sąraše
                                is_top_destination = dest in TOP_DESTINATIONS
                                is_ideal_weekend = (
                                    out_datetime.weekday() == 4 and out_datetime.hour <= 12 and
                                    in_datetime.weekday() == 6 and in_datetime.hour >= 15
                                )
                                tags = ""
                                if is_ideal_weekend: tags += "⭐ *IDEALUS SAVAITGALIS!*\n"
                                if is_top_destination: tags += "🔥 *TOP KRYPTIS!*\n"
                                if origin == "VNO": tags += "🔝 *Prioritetas: Vilnius*\n"

                                msg = (
                                    f"{tags}🔄 *RADAU KELIONĘ Į ABI PUSES!*\n\n"
                                    f"📍 *Kryptis:* {origin} <-> {out_f.destinationFull} ({dest})\n"
                                    f"💰 *Bendra kaina:* {total_price:.2f}€\n"
                                    f"📅 *Trukmė:* {stay_duration} d.\n\n"
                                    f"🛫 *Išskrenda ({origin}):* {out_time_clean} ({out_f.price:.2f}€)\n"
                                    f"🛬 *Grįžta ({dest}):* {in_time_clean} ({in_f.price:.2f}€)"
                                )
                                print(f" Rasta kelionė į {out_f.destinationFull} ({total_price:.2f}€)")
                                send_telegram_message(msg)
                                time.sleep(1.5)
        except Exception as e:
            print(f"Klaida standartinėje paieškoje iš {origin}: {e}")

if __name__ == "__main__":
    api_instance = Ryanair(CURRENCY)
    tomorrow_dt = datetime.now() + timedelta(days=1)
    search_end_dt = datetime.now() + timedelta(days=180)

    print(f"--- Skenuoju Ryanair ({datetime.now().strftime('%H:%M:%S')}) ---")
    
    search_italy_triangle(api_instance, tomorrow_dt, search_end_dt)
    search_standard_flights(api_instance, tomorrow_dt, search_end_dt)
    
    print("\nPaieška baigta!")