import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import sys
from urllib.request import urlopen
import xml.etree.ElementTree as ET

SOURCE = "http://186.246.3.176/HG_direct_v3.yml"
ROOT = Path(__file__).resolve().parents[1]


def read_table(filename, columns):
    with (ROOT / filename).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["offer_id", *columns]:
            raise ValueError(f"Unexpected header in {filename}")
        rows = {}
        for row in reader:
            offer_id = row.pop("offer_id")
            if not offer_id or offer_id in rows or None in row or any(not value for value in row.values()):
                raise ValueError(f"Invalid or duplicate offer ID in {filename}: {offer_id}")
            rows[offer_id] = row
        if not rows:
            raise ValueError(f"No offers in {filename}")
        return rows


def build(source):
    labels = read_table("hobby_games_offer_labels.csv", ["custom_label_3", "custom_label_4"])
    sale = read_table("hobbygames_sale_discounts.csv", ["discount_percent", "custom_score"])
    for row in sale.values():
        if row["custom_score"] != "509" or not 0 < int(row["discount_percent"]) < 100:
            raise ValueError("Invalid sale score or discount")

    tree = ET.parse(source)
    offers = tree.findall("./shop/offers/offer")
    if tree.getroot().tag != "yml_catalog" or not offers:
        raise ValueError("Source is not a YML feed with offers")
    seen = set()
    discounted = 0
    for offer in offers:
        offer_id = offer.get("id")
        if not offer_id or offer_id in seen:
            raise ValueError(f"Invalid or duplicate source offer ID: {offer_id}")
        seen.add(offer_id)
        for field in ("custom_label_3", "custom_label_4", "custom_score"):
            if offer.find(field) is not None:
                raise ValueError(f"Source already contains {field} for {offer_id}")
        for field in ("custom_label_3", "custom_label_4"):
            ET.SubElement(offer, field).text = labels.get(offer_id, {}).get(field, "base")
        promotion = sale.get(offer_id)
        ET.SubElement(offer, "custom_score").text = promotion["custom_score"] if promotion else "0"
        if promotion:
            prices = offer.findall("price")
            if len(prices) != 1 or not prices[0].text:
                raise ValueError(f"Expected one price for {offer_id}")
            price = prices[0]
            current = Decimal(price.text)
            if not current.is_finite() or current <= 0:
                raise ValueError(f"Invalid price for {offer_id}")
            multiplier = Decimal(100 - int(promotion["discount_percent"])) / 100
            final = (current * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            price.text = format(final, "f").rstrip("0").rstrip(".")
            discounted += 1

    target = ROOT / "hobbygames-sale.yml"
    temporary = target.with_suffix(".tmp")
    tree.write(temporary, encoding="UTF-8", xml_declaration=True)
    temporary.replace(target)
    print(f"Offers: {len(offers)}. Sale: {discounted}. Sale IDs absent in source: {len(sale)-discounted}.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        build(sys.argv[1])
    else:
        with urlopen(SOURCE, timeout=60) as response:
            build(response)
