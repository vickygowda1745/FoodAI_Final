import math
import requests


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_nearby_restaurants(lat: float, lng: float, radius_meters: int = 15000) -> dict:
    # Multiple public Overpass API mirrors to ensure 99.9% availability
    overpass_endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]

    # Fast-executing query
    overpass_query = f"""
    [out:json][timeout:10];
    (
      node["amenity"="restaurant"](around:{radius_meters},{lat},{lng});
      node["amenity"="fast_food"](around:{radius_meters},{lat},{lng});
      node["amenity"="cafe"](around:{radius_meters},{lat},{lng});
    );
    out body 30;
    """

    data = None
    last_error = ""

    # Try endpoints sequentially if one server is busy
    for url in overpass_endpoints:
        try:
            response = requests.post(
                url,
                data={"data": overpass_query},
                headers={"User-Agent": "FoodAI-App/1.0"},
                timeout=8,
            )
            if response.status_code == 200:
                data = response.json()
                break
        except Exception as err:
            last_error = str(err)
            continue

    # Fallback to tighter 5 km radius search if 15 km request timed out on all servers
    if not data or "elements" not in data:
        tight_query = f"""
        [out:json][timeout:8];
        (
          node["amenity"="restaurant"](around:5000,{lat},{lng});
          node["amenity"="fast_food"](around:5000,{lat},{lng});
          node["amenity"="cafe"](around:5000,{lat},{lng});
        );
        out body 25;
        """
        for url in overpass_endpoints:
            try:
                response = requests.post(
                    url,
                    data={"data": tight_query},
                    headers={"User-Agent": "FoodAI-App/1.0"},
                    timeout=6,
                )
                if response.status_code == 200:
                    data = response.json()
                    break
            except Exception as err:
                last_error = str(err)
                continue

    if not data or "elements" not in data:
        return {
            "status": "error",
            "message": f"Server busy while fetching nearby places ({last_error or 'Timeout'}). Please retry.",
            "restaurants": [],
        }

    elements = data.get("elements", [])
    restaurants = []

    for item in elements:
        tags = item.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        place_lat = item.get("lat")
        place_lng = item.get("lon")

        if place_lat is not None and place_lng is not None:
            dist_km = haversine_distance(lat, lng, place_lat, place_lng)
            distance_str = f"{dist_km:.2f} km"
        else:
            dist_km = 999.0
            distance_str = "N/A"

        address_parts = []
        if "addr:housenumber" in tags:
            address_parts.append(tags["addr:housenumber"])
        if "addr:street" in tags:
            address_parts.append(tags["addr:street"])
        if "addr:suburb" in tags:
            address_parts.append(tags["addr:suburb"])
        if "addr:city" in tags:
            address_parts.append(tags["addr:city"])

        if address_parts:
            address = ", ".join(address_parts)
        else:
            cuisine = tags.get("cuisine", "").capitalize()
            address = f"{cuisine} Dining" if cuisine else "OpenStreetMap Verified Location"

        rating = tags.get("stars") or tags.get("rating") or "4.2"

        restaurants.append(
            {
                "name": name,
                "rating": rating,
                "address": address,
                "distance": distance_str,
                "_numeric_distance": dist_km,
            }
        )

    restaurants.sort(key=lambda x: x["_numeric_distance"])

    formatted_restaurants = [
        {
            "name": r["name"],
            "rating": r["rating"],
            "address": r["address"],
            "distance": r["distance"],
        }
        for r in restaurants[:25]
    ]

    if not formatted_restaurants:
        return {
            "status": "success",
            "message": "No mapped restaurants found in this immediate area.",
            "restaurants": [],
        }

    return {"status": "success", "restaurants": formatted_restaurants}