import requests
import time
import math
from typing import List
from models import PartLine

MOUSER_SEARCH_URL = "https://api.mouser.com/api/v1/search/partnumber"


def fetch_mouser_data(parts: List[PartLine], api_key: str):
    """
    The main manager function.
    It loops through your parts list and asks Mouser about each one.
    """
    if not api_key:
        print("Error: No API key provided.")
        return

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    print(f"--- Contacting Mouser for {len(parts)} parts ---")

    #Process one part at a time
    for i, part in enumerate(parts):

        # Skip empty rows or parts we already know are bad
        if not part.mpn or "MISSING" in part.mpn:
            part.status = "Skipped"
            continue

        print(f"Checking [{i + 1}/{len(parts)}]: {part.mpn}...")

        payload = {
            "SearchByPartRequest": {
                "mouserPartNumber": part.mpn,
                "partSearchOptions": "Exact"
            }
        }

        try:
            # Send the truck to the URL with our Key and Payload
            full_url = f"{MOUSER_SEARCH_URL}?apiKey={api_key}"
            response = requests.post(full_url, headers=headers, json=payload, timeout=10)

            # Did the server say "OK" (Code 200)?
            if response.status_code == 200:
                data = response.json()
                _process_mouser_response(part, data)
            else:
                part.status = f"API Error {response.status_code}"

        except Exception as e:
            print(f"Connection error on {part.mpn}: {e}")
            part.status = "Error"

        # 6. Be Polite: Wait 0.5 seconds so Mouser doesn't ban us for spamming.
        time.sleep(0.5)

    print("--- Mouser Search Complete ---")


def _process_mouser_response(part: PartLine, data: dict):
    # Error Checking
    errors = data.get("Errors", [])
    if errors:
        error_msg = str(errors[0].get("Message", "Unknown Error"))
        print(f"  !! Mouser API Error for {part.mpn}: {error_msg}")
        part.status = "API Error"
        return

    results = data.get("SearchResults")
    if not results:
        part.status = "No Data"
        return

    if results.get("NumberOfResult", 0) > 0:
        match = results["Parts"][0]

        part.supplier = "Mouser"
        part.supplier_pn = match.get("MouserPartNumber", "")
        part.manufacturer = match.get("Manufacturer", "")
        part.link = match.get("ProductDetailUrl", "")

        # STOCK PARSING
        stock_val = 0
        raw_factory = str(match.get("FactoryStock", "0")).replace(",", "")
        try:
            stock_val = int(raw_factory)
        except ValueError:
            stock_val = 0

        if stock_val == 0:
            avail_str = match.get("Availability", "")
            if avail_str:
                first_part = avail_str.split(" ")[0]
                clean_part = first_part.replace(",", "")
                try:
                    stock_val = int(clean_part)
                except ValueError:
                    pass
        part.stock_available = stock_val

        # STRICT RULES (Min/Mult)
        try:
            min_qty = int(match.get("Min", "1"))
        except ValueError:
            min_qty = 1
        try:
            mult_qty = int(match.get("Mult", "1"))
        except ValueError:
            mult_qty = 1

        buy_qty = part.qty

        # Enforce Minimum
        if buy_qty < min_qty:
            buy_qty = min_qty

        # Enforce Multiples (Standard Packs)
        remainder = buy_qty % mult_qty
        if remainder != 0:
            buy_qty += (mult_qty - remainder)

        # SMART UPGRADE (Economic Optimization)
        # If buying the next tier up costs roughly the same, do it.

        price_breaks = match.get("PriceBreaks", [])
        best_price = 0.0

        if price_breaks:
            # find the price for our current strict 'buy_qty'
            current_unit_price = 0.0
            for pb in price_breaks:
                tier_qty = pb.get("Quantity", 0)
                if tier_qty <= buy_qty:
                    try:
                        current_unit_price = float(pb.get("Price", "0").replace("$", ""))
                    except:
                        pass

            # Now look at higher tiers to see if we should upgrade
            current_total_cost = buy_qty * current_unit_price

            for pb in price_breaks:
                tier_qty = pb.get("Quantity", 0)
                try:
                    tier_price = float(pb.get("Price", "0").replace("$", ""))
                except:
                    continue

                # Only check tiers BIGGER than what we plan to buy
                if tier_qty > buy_qty:
                    tier_total_cost = tier_qty * tier_price

                    cost_diff = tier_total_cost - current_total_cost

                    if cost_diff < 0.50:
                        print(
                            f"  -> Smart Upgrade for {part.mpn}: {buy_qty} @ ${current_unit_price} -> {tier_qty} @ ${tier_price} (Diff: ${cost_diff:.2f})")
                        buy_qty = tier_qty
                        current_unit_price = tier_price
                        current_total_cost = tier_total_cost
                        # Stop looking once we upgrade once
                        break

            best_price = current_unit_price

        # Fallback if no price found
        if best_price == 0 and price_breaks:
            try:
                best_price = float(price_breaks[0].get("Price", "0").replace("$", ""))
            except:
                pass

        # Update the Part Object with the new "Optimized" Quantity
        if part.qty != buy_qty:
            part.qty = buy_qty

        part.unit_price = best_price
        part.total_price = part.unit_price * part.qty

        if part.stock_available >= part.qty:
            part.status = "In Stock"
        else:
            part.status = "Low Stock"
    else:
        part.status = "Not Found"