from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

UNSPLASH_ACCESS_KEY = "CVCGyPskgBwfmVDGKRF9EfKb9PqkA29lbictam9smAA"  # Set your Unsplash access key here


@app.route('/city-image/<city_name>')
def get_city_image(city_name):
    try:
        # Fetch photo of the city from Unsplash
        response = requests.get(
            f"https://api.unsplash.com/search/photos?query={city_name}&orientation=landscape",
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()

        # Extract image URL and user information from the response
        photo = data["results"][0]
        image_urls = photo["urls"]
        user_name = photo["user"]["name"]
        user_username = photo["user"]["username"]

        return render_template('trail.html', image_urls=image_urls, user_name=user_name, user_username=user_username)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
