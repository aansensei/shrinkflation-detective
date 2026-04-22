# Phase 2 -- parsing weight_raw into actual numbers we can compare
# there are tons of ways that people write weights, such as 6 oz and 40g.
# we cannot compare those two without converting them to a common unit.
# so we need to parse the weight_raw field into a number and a unit, and then convert it to a common unit (e.g. grams) using regexes and a conversion table.
import re
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text
from tqdm import tqdm  # I mean having a loading bar is fun:)))))

load_dotenv()  # Loading environemtal variables from .env file

# conversion table -- everything maps to grams or ml
# why a dict? easy to add new units later without touching the logic
UNIT_TO_GRAMS = {
    "oz":  28.3495,
    "lb":  453.592,
    "g":   1.0,
    "kg":  1000.0,
}

UNIT_TO_ML = {
    "fl oz":  29.5735,
    "fl. oz": 29.5735,  # some products write it with a period
    "ml":     1.0,
    "l":      1000.0,
    "liter":  1000.0,
    "qt":     946.353,
    "gal":    3785.41,
    "pt":     473.176,
}

# turns out a ton of products don't have weight at all -- they're sold by count
# think eggs (12 ct), paper towels (6 rolls), chip bags (30 ct)
# we can't convert "16 ct" to grams but we CAN still catch shrinkflation
# if next week the same product is "12 ct" at the same price, that's a red flag
UNIT_TO_COUNT = {
    "ct":     1.0,
    "count":  1.0,
    "rolls":  1.0,
    "roll":   1.0,
    "rl":     1.0,  # short for rolls
    "pk":     1.0,
    "pack":   1.0,
    "wipes":  1.0,
    "sheets": 1.0,
    "quart":  1.0,  # rare but shows up as a count label
}


def parse_weight(weight_raw):
    # returns (amount, unit) or (None, None) if we can't figure it out
    # None means this row gets flagged for manual review later
    if not weight_raw:  # ignore emty or null things that we can't parse
        return None, None

    text = weight_raw.lower().strip()  # normalize case and whitespace

    # all units we know how to handle -- fl oz must come before oz
    # otherwise "32 fl oz" would match as "32 f" + "oz" which is wrong
    # we want to try ml units first since they are more specific (e.g. "fl oz" vs "oz")
    known_units = list(UNIT_TO_ML.keys()) + \
        list(UNIT_TO_GRAMS.keys()) + list(UNIT_TO_COUNT.keys())
    units_pattern = "|".join(re.escape(u) for u in known_units)

    # multi-pack pattern: "12 x 1.5 oz" or "6x2 fl oz"
    multi = re.search(
        # super long regex :)))))
        rf"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)\s*({units_pattern})",
        text
    )
    if multi:
        count = float(multi.group(1))
        amount = float(multi.group(2))
        unit = multi.group(3).strip()
        return round(count * amount, 4), unit

    # single value pattern: "16 oz", "500 g", "2 l"
    single = re.search(
        rf"(\d+(?:\.\d+)?)\s*({units_pattern})",
        text
    )
    if single:
        amount = float(single.group(1))
        unit = single.group(2).strip()
        return amount, unit

    return None, None  # couldn't parse, will show up in quality check later


def convert_to_standard(amount, unit):
    # takes the (amount, unit) from parse_weight and converts to a standard unit
    # solid goods -> grams, liquid goods -> ml
    # returns (normalized_amount, "g") or (normalized_amount, "ml") or (None, None)
    if amount is None or unit is None:
        return None, None

    if unit in UNIT_TO_GRAMS:
        return round(amount * UNIT_TO_GRAMS[unit], 4), "g"

    if unit in UNIT_TO_ML:
        return round(amount * UNIT_TO_ML[unit], 4), "ml"

    if unit in UNIT_TO_COUNT:
        # just store the count as-is, unit becomes "ct"
        return round(amount * UNIT_TO_COUNT[unit], 4), "ct"

    return None, None  # unknown unit slipped through


def normalize(weight_raw, price):
    # one-stop function: give it the raw string + price, and it returns the normalized weight, standard unit, and price per unit
    # get back everything we need to store in the snapshots table
    amount, unit = parse_weight(weight_raw)
    normalized, standard_unit = convert_to_standard(amount, unit)

    if normalized and price and normalized > 0:
        # weight/volume -> price per 100g or 100ml (standard comparison unit)
        # count -> price per single item makes more sense than per 100 items
        multiplier = 1 if standard_unit == "ct" else 100
        price_per_unit = round((price / normalized) * multiplier, 4)
    else:
        price_per_unit = None

    return normalized, standard_unit, price_per_unit


def run_normalization(engine):
    # grab every snapshot that hasn't been normalized yet
    # we only process NULL rows so it's safe to run multiple times
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, weight_raw, price
            FROM snapshots
            WHERE weight_normalized IS NULL
        """)).fetchall()

    print(f"Found {len(rows)} snapshots to normalize.\n")

    updated = 0
    failed = 0

    with engine.begin() as conn:  # we want to batch all updates in a single transaction for speed and atomicity
        # INITIATE the BARRRRRRRRRRRRRRRRRRRRR:)))))
        for row in tqdm(rows, desc="Normalizing", unit="row"):
            snap_id = row[0]
            weight_raw = row[1]
            price = row[2]

            normalized, unit, price_per_unit = normalize(weight_raw, price)

            if normalized:
                conn.execute(text("""
                    UPDATE snapshots
                    SET weight_normalized = :wn,
                        weight_unit       = :wu,
                        price_per_unit    = :ppu
                    WHERE id = :id
                """), {
                    "wn":  normalized,
                    "wu":  unit,
                    "ppu": price_per_unit,
                    "id":  snap_id,
                })
                updated += 1
            else:
                failed += 1

    print(f"Updated : {updated}")
    print(f"Failed  : {failed}  (weight_raw couldn't be parsed)")
    print(f"Parse accuracy: {round(updated / len(rows) * 100, 1)}%")


def main():  # entry point for the script
    engine = create_engine(os.getenv("NEON_DB_URL"))
    run_normalization(engine)


if __name__ == "__main__":  # only run if this script is executed directly, not if it's imported as a module
    main()
