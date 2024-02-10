from amadeus import Client, ResponseError, analytics
import requests


## calc_lat_long will calculate the latitude and longitude of the given address and nearby airport
## return from_lat, from_long , to_lat ,to_long
def calc_lat_long(add):
    url = "https://address-from-to-latitude-longitude.p.rapidapi.com/geolocationapi"

    querystring = {"address": add}

    headers = {
        "X-RapidAPI-Key": '46b2411b49msh40cf2b346bc2a84p18f5ffjsn463cab377871',
        "X-RapidAPI-Host": "address-from-to-latitude-longitude.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)
    data = response.text
    print(data)
    print(response.json())
    from_lat = response.json()['Results'][0]["latitude"]
    from_long = response.json()['Results'][0]["longitude"]
    # city = response.json()['Results'][0]["city"]
    # print(from_lat, from_long)

    amadeus = Client(
        client_id='7KUpum4cjVAHkMvdn0GR0nbrIzYFGHd0',
        client_secret='n8ZUaNGtyIDRwuBY'
    )

    try:
        # lat = 12.8699
        # long = 80.2184
        response = amadeus.reference_data.locations.airports.get(
            longitude=from_long,
            latitude=from_lat,
        )
        # print(response.data)
        airport_name = response.data[0]['name']
        airport_code = response.data[0]['iataCode']
        to_lat = response.data[0]['geoCode']["latitude"]
        to_long = response.data[0]['geoCode']["longitude"]
        dist = response.data[0]['distance']["value"]

    except ResponseError as error:
        print(error)
    return from_lat, from_long, airport_name, airport_code, to_lat, to_long, dist
