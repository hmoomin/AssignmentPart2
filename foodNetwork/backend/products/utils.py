import math
import requests

def postcode_to_coords(postcode):
    try:
        res = requests.get(f"https://api.postcodes.io/postcodes/{postcode}", timeout=3)
        data = res.json()
        if data["status"] != 200 or not data["result"]:
            raise ValueError("Invalid postcode")
        return data["result"]["latitude"], data["result"]["longitude"]
    except Exception:
        return None, None

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3958.8  # miles
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2

    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))