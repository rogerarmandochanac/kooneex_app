from math import (radians, 
                    cos, 
                    sin, 
                    asin, 
                    sqrt
                )

def calcular_distancia(lat1, lon1, lat2, lon2):
    """Calcula la distancia entre dos coordenadas (en kilómetros)."""
    R = 6371  # radio de la Tierra en km
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c