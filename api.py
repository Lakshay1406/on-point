from amadeus import Client, ResponseError, analytics
import requests


## calc_lat_long will calculate the latitude and longitude of the given address and nearby airport
## return from_lat, from_long , to_lat ,to_long
def calc_lat_long(add):
    url = "https://address-from-to-latitude-longitude.p.rapidapi.com/geolocationapi"

    querystring = {"address": add}

    headers = {
        "X-RapidAPI-Key": "23f0a5b85cmsh83140e0a39e0664p11dbefjsnd7193ad7a38b",
        "X-RapidAPI-Host": "address-from-to-latitude-longitude.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params=querystring)

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
        #print(response.data)
        airport_name = response.data[0]['name']
        airport_code = response.data[0]['iataCode']
        to_lat = response.data[0]['geoCode']["latitude"]
        to_long = response.data[0]['geoCode']["longitude"]

    except ResponseError as error:
        print(error)
    return from_lat, from_long, airport_name, airport_code, to_lat, to_long
