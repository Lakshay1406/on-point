import requests as requests
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, abort
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from api import calc_lat_long
# from train import get_city_from_address,get_tickets_from_stcode
from werkzeug.utils import secure_filename
import os
from functools import wraps
from http import HTTPStatus
from datetime import datetime
from amadeus import Client, ResponseError
from OpenAI_API_script import search_destinations, find_nearest_station, find_nearest_airport
from train import get_tickets_from_stcode
from dotenv import load_dotenv
load_dotenv()

TEST_MODE = True
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
bootstrap = Bootstrap5(app)
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

login_manager = LoginManager()
login_manager.init_app(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)

#API_keys
rapid_api_key_for_train = 'ed61e1e291msh3180b8a78efa8bep16aeeajsn136814a859fa'
rapid_api_key_for_lat_long='3813f5e554msheaa31e90e985c7ep116172jsn0ce5a97bccf5'
# also check usage on openAPI


# CONFIGURE TABLES
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    phone_no = db.Column(db.Integer)


class Train(db.Model, UserMixin):
    __tablename__ = "train"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True)
    st_name = db.Column(db.String(100))
    place = db.Column(db.String(100))


class Api(db.Model, UserMixin):
    __tablename__ = "api"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    count = db.Column(db.Integer)


# Create a user_loader callback
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


@login_manager.unauthorized_handler
def unauthorized():
    if request.blueprint == 'api':
        abort(HTTPStatus.UNAUTHORIZED)
    flash('login / signup is required')
    return redirect(url_for('login'))


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    return render_template('index.html')


@app.route("/loading", methods=["POST"])
def loading():
    if request.method == "POST":
        # We'll use a session object to save the data sent by the user for processing
        session["start_add"] = request.form.get("start")
        session["end_add"] = request.form.get('end')
        session["indate"] = request.form.get('in-date')
        session["adult"] = request.form.get('adult')
        return render_template("loading.html")


@app.route('/abcd', methods=["GET", "POST"])
def abcd():
    start_add = session["start_add"]
    end_add = session["end_add"]
    indate = session["indate"]
    adult = session["adult"]
    print(start_add, end_add, indate, adult)

    start_calc = calc_lat_long(start_add,rapid_api_key_for_lat_long)

    ##coordinates saved in session
    session["st_from_lat"] = start_calc["from_lat"]
    session["st_from_long"] = start_calc["from_long"]
    session["st_to_lat"] = start_calc["to_lat"]
    session["st_to_long"] = start_calc["to_long"]

    # converting to IATA code for flight search
    start = start_calc["airport_code"]
    start_air = start_calc["airport_name"].capitalize()
    session["start_air"] = start_air

    ## assuming cab fare to be rs 15 per km
    ## assuming cab travels at 30km/hr
    start_fare = start_calc["dist"] * 15
    start_cab_time = int((start_calc["dist"] / 30) * 60)

    ## end_location
    end_calc = calc_lat_long(end_add,rapid_api_key_for_lat_long)
    ##coordinates saved in session
    session["ed_from_lat"] = end_calc["from_lat"]
    session["ed_from_long"] = end_calc["from_long"]
    session["ed_to_lat"] = end_calc["to_lat"]
    session["ed_to_long"] = end_calc["to_long"]

    end = end_calc["airport_code"]
    end_air = end_calc["airport_name"].capitalize()
    session["end_air"] = end_air
    end_fare = end_calc["dist"] * 15
    end_cab_time = int((end_calc["dist"] / 30) * 60)
    print(start, end, start_calc["dist"], end_calc["dist"])

    # flight offer search api calling and getting required values

    amadeus = Client(
        client_id='7KUpum4cjVAHkMvdn0GR0nbrIzYFGHd0',
        client_secret='n8ZUaNGtyIDRwuBY'
    )
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=start,
            destinationLocationCode=end,
            departureDate=indate,
            adults=adult,
            currencyCode='INR',
            max=4,

        )
        l = response.data
        print(l)
        flights = []
        for i in l:
            flg = []
            n = len(i["itineraries"][0]["segments"]) - 1
            flg.append(i["itineraries"][0]["duration"].lstrip('PT'))
            flg.append((i["itineraries"][0]["segments"][0]["departure"]["at"].split('T'))[1][:-3])
            flg.append((i["itineraries"][0]["segments"][n]["arrival"]["at"].split('T'))[1][:-3])

            code = i["itineraries"][0]["segments"][0]["carrierCode"]
            if code != 'FZ':
                url = "https://aviation-reference-data.p.rapidapi.com/airline/" + code

                headers = {
                    "X-RapidAPI-Key": "3813f5e554msheaa31e90e985c7ep116172jsn0ce5a97bccf5",
                    "X-RapidAPI-Host": "aviation-reference-data.p.rapidapi.com"
                }

                response = requests.get(url, headers=headers)

                flg.append(response.json()['name'])
            else:
                flg.append("FlyDubai")
            flg.append(n)
            price = i["price"]["total"][:-3]
            s, *d = str(price).partition(".")
            r = ",".join([s[x - 2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
            price = "".join([r] + d)
            flg.append(price)
            flights.append(flg)
            print(flg)
        return render_template('abcd.html', start_cab_time=start_cab_time, end_cab_time=end_cab_time,
                               start_fare=start_fare, end_fare=end_fare, start_add=start_add, end_add=end_add,
                               start_air=start_air, end_air=end_air, flights=flights)
    except ResponseError as error:
        print(error)


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        genpassword = generate_password_hash(request.form["password"], method='pbkdf2:sha256', salt_length=8)
        email = request.form.get('email')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash('Email already exists.Try logging in instead.')
            return redirect(url_for('login'))
        new_user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=genpassword,
            age=request.form.get('age'),
            phone_no=request.form.get('phone_no')
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        return redirect(url_for("plan"))
    return render_template("register.html")


@app.route('/map', methods=["GET", "POST"])
def map():
    num = int(request.args.get('id'))
    print(num)
    if num == 1:
        start_add = session["start_add"]
        end_add = session["start_air"]
        from_lat = session["st_from_lat"]
        from_long = session["st_from_long"]
        to_lat = session["st_to_lat"]
        to_long = session["st_to_long"]
    elif num == 2:
        start_add = session["end_air"]
        end_add = session["end_add"]
        to_lat = session["ed_from_lat"]
        to_long = session["ed_from_long"]
        from_lat = session["ed_to_lat"]
        from_long = session["ed_to_long"]
    cords = {'start_add': start_add, 'end_add': end_add, 'from_lat': from_lat, 'from_long': from_long, 'to_lat': to_lat,
             'to_long': to_long}
    return render_template('map.html', cords=cords)


@app.route('/plan', methods=["GET", "POST"])
def plan():
    # if request.method == 'POST':
    #     start_add = request.form.get('start')
    #     end_add = request.form.get('end')
    #     indate = request.form.get('in-date')
    #     # outdate = request.form.get('out-date')
    #     adult = request.form.get('adult')
    #     # child = request.form.get('child')

    return render_template('plan.html')


@app.route('/final', methods=["GET", "POST"])
def final():
    start_add = request.args.get('start_add')
    end_add = request.args.get('end_add')
    flg = request.args.getlist('flg')
    flg = flg[0].strip('[]').split(',')
    flg = [i.strip("/"" '") for i in flg]
    start_air = request.args.get('start_air')
    end_air = request.args.get('end_air')

    start_fare = request.args.get('start_fare')
    end_fare = request.args.get('end_fare')
    start_cab_time = request.args.get('start_cab_time')
    end_cab_time = request.args.get('end_cab_time')

    print(flg)
    return render_template('final.html', start_cab_time=start_cab_time, end_cab_time=end_cab_time,
                           start_fare=start_fare, end_fare=end_fare, start_air=start_air, end_air=end_air, flg=flg,
                           end_add=end_add, start_add=start_add)


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if not user:
            flash('Invalid email provided')
            return render_template("login.html")
        if check_password_hash(user.password, password):
            login_user(user)

            return redirect(url_for('plan'))
        else:
            flash('Password incorrect, please try again')
            return render_template("login.html")
    return render_template("login.html")


# @app.route('/train', methods=["GET", "POST"])
# def train():
#     # start= "Off, Old Mahabalipuram Road, Kamaraj Nagar, Semmancheri, Chennai, Tamil Nadu 600119"
#     # end="Kasturba Rd, behind High Court of Karnataka, Ambedkar Veedhi, Sampangi Rama Nagara, Bengaluru, Karnataka 560001"
#     begin = find_nearest_station(start)
#     print(begin)
#     to = find_nearest_station(end)
#     print(to)
#
#
#     date='2024-04-03'
#     l=get_tickets_from_stcode(begin,to,date,rapid_api_key_for_train)
#
#
#
#
#     return redirect(url_for('home'))


@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/budget')
def budget():
    return render_template('budget.html')


@app.route('/destinations', methods=["GET", "POST"])
def destinations():
    address = session['budget_start_add']
    budget = session['budget_budget']
    date = session['budget_date']
    print(address, budget, date)
    destinations = search_destinations(address + ' ' + budget)
    # print(destinations)
    return render_template('destinations.html', destinations=destinations)



@app.route("/loading_locations", methods=["POST"])###loading nearby destinations
def loading_locations():
    if request.method == "POST":
        session['budget_start_add']=request.form.get('address')
        session['budget_budget']=request.form.get('budget')
        session['budget_date']=request.form.get('date')
        return render_template("loading_locations.html")

@app.route("/loading_destination")### for long load after selecting city
def loading_destination():
    session['budget_city'] = request.args.get('city')
    print(session['budget_city'])
    return render_template("loading_destination.html")


@app.route('/details')
def details():
    city = session['budget_city']
    print("got" + city)
    if TEST_MODE == True:
        ## details for chennai to kodaikanal for budget 50000
        train_details = [
            {'train_number': '20665', 'train_name': 'Vande Bharat Express', 'duration': '5:40', 'from': 'MS',
             'to': 'MDU', 'departure_time': '14:50', 'arrival_time': '20:30', 'from_station_name': 'CHENNAI EGMORE',
             'to_station_name': 'MADURAI JN', 'class': 'CC', 'fare': 1005},
            {'train_number': '16101', 'train_name': 'Chennai Egmore - Kollam Express', 'duration': '7:10', 'from': 'MS',
             'to': 'MDU', 'departure_time': '17:00', 'arrival_time': '00:10', 'from_station_name': 'CHENNAI EGMORE',
             'to_station_name': 'MADURAI JN', 'class': '3A', 'fare': 790},
            {'train_number': '12661', 'train_name': 'Pothigai SF Express', 'duration': '7:25', 'from': 'MS',
             'to': 'MDU', 'departure_time': '20:40', 'arrival_time': '04:05', 'from_station_name': 'CHENNAI EGMORE',
             'to_station_name': 'MADURAI JN', 'class': '1A', 'fare': 1960}]
        start_iata = 'MAA'
        end_iata = 'CJB'
        start_air = 'Chennai International Airport'
        end_air = 'Coimbatore International Airport'
        flights = [['1H10M', '13:20', '14:30', 'AIR INDIA', 0, '5,587'],
                   ['6H55M', '07:00', '13:55', 'VISTARA', 1, '11,367'],
                   ['17H25M', '20:30', '13:55', 'VISTARA', 1, '11,367'],
                   ['25H25M', '12:30', '13:55', 'VISTARA', 1, '12,078']]

        return render_template('details.html', train_details=train_details, start_iata=start_iata, end_iata=end_iata,
                               start_air=start_air, end_air=end_air, flights=flights)

    ### calculating possible train routes
    begin = find_nearest_station(session['budget_start_add'])
    print(begin)
    to = find_nearest_station(city)
    print(to)
    date = session['budget_date']
    if to == None:
        train_details = []
    else:
        train_details = get_tickets_from_stcode(begin, to, date, rapid_api_key_for_train)

    #### calculating possible flight routes

    # calculating IATA code and name
    data1 = find_nearest_airport(session['budget_start_add'])
    start_iata = data1['IATA-code']
    start_air = data1['airport name']

    data2 = find_nearest_airport(city)
    end_iata = data2['IATA-code']
    try:
        end_air = data2['airport name']
    except:
        end_air = data2['Airport name']

    print(start_iata, end_iata)
    '''start_calc = calc_lat_long(session['budget_start_add'], rapid_api_key_for_lat_long)
    start_iata=start_calc["airport_code"]
    start_air=start_calc["airport_name"]

    end_calc = calc_lat_long(city, rapid_api_key_for_lat_long)
    end_iata = end_calc["airport_code"]
    end_air = end_calc["airport_name"]
    print(start_iata, end_iata)'''
    if start_iata==end_iata:
        flights = []
        return render_template('details.html', train_details=train_details, start_iata=start_iata, end_iata=end_iata,
                               start_air=start_air, end_air=end_air, flights=flights)
    # flight offer search api calling and getting required values

    amadeus = Client(
        client_id='7KUpum4cjVAHkMvdn0GR0nbrIzYFGHd0',
        client_secret='n8ZUaNGtyIDRwuBY'
    )
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=start_iata,
            destinationLocationCode=end_iata,
            departureDate=date,
            adults=1,
            currencyCode='INR',
            max=4,

        )
        l = response.data
        print(l)
        flights = []
        for i in l:
            flg = []
            n = len(i["itineraries"][0]["segments"]) - 1
            flg.append(i["itineraries"][0]["duration"].lstrip('PT'))
            flg.append((i["itineraries"][0]["segments"][0]["departure"]["at"].split('T'))[1][:-3])
            flg.append((i["itineraries"][0]["segments"][n]["arrival"]["at"].split('T'))[1][:-3])

            code = i["itineraries"][0]["segments"][0]["carrierCode"]
            if code != 'FZ':
                url = "https://aviation-reference-data.p.rapidapi.com/airline/" + code

                headers = {
                    "X-RapidAPI-Key": "3813f5e554msheaa31e90e985c7ep116172jsn0ce5a97bccf5",
                    "X-RapidAPI-Host": "aviation-reference-data.p.rapidapi.com"
                }

                response = requests.get(url, headers=headers)

                flg.append(response.json()['name'])
            else:
                flg.append("FlyDubai")
            flg.append(n)
            price = i["price"]["total"][:-3]
            s, *d = str(price).partition(".")
            r = ",".join([s[x - 2:x] for x in range(-3, -len(s), -2)][::-1] + [s[-3:]])
            price = "".join([r] + d)
            flg.append(price)
            flights.append(flg)
            print(flg)
    except ResponseError as error:
        print(error)
    print("successfully processed details")
    return render_template('details.html', train_details=train_details, start_iata=start_iata, end_iata=end_iata,
                           start_air=start_air, end_air=end_air, flights=flights)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
