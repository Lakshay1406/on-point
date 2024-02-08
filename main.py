import requests as requests
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_bootstrap import Bootstrap5
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from api import calc_lat_long
from werkzeug.utils import secure_filename
import os
from functools import wraps
from http import HTTPStatus
from datetime import datetime
from amadeus import Client, ResponseError

app = Flask(__name__)
app.config['SECRET_KEY'] = '8Badawdawdb'
bootstrap = Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()
db.init_app(app)


# CONFIGURE TABLES
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    phone_no = db.Column(db.Integer)


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


@app.route('/abcd', methods=["GET", "POST"])
def abcd():
    return render_template('abcd.html')

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        genpassword = generate_password_hash(request.form["password"], method='pbkdf2:sha256', salt_length=8)
        email = request.form.get('email')
        result = db.session.execute(db.select(User).where(User.email == email))
        user = result.scalar()
        if user:
            flash('Email already exists.Try logging in instead. ')
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
    num=int(request.args.get('id'))
    print(num)
    if num==1:
        print('hi')
        start_add =request.args.get('start_add')
        print(start_add)
        calc = calc_lat_long(start_add)
        end_add = calc[2]
        from_lat = calc[0]
        from_long = calc[1]
        to_lat = calc[4]
        to_long = calc[5]
    elif num==2:
        print('bye')
        end_add =request.args.get('end_add')
        calc = calc_lat_long(end_add)
        start_add = calc[2]
        from_lat = calc[4]
        from_long = calc[5]
        to_lat = calc[0]
        to_long = calc[1]
    cords = {'start_add': start_add, 'end_add': end_add, 'from_lat': from_lat, 'from_long': from_long, 'to_lat': to_lat,
             'to_long': to_long}
    return render_template('map.html', cords=cords)


@app.route('/plan', methods=["GET", "POST"])
def plan():
    if request.method == 'POST':
        start_add = request.form.get('start')
        end_add = request.form.get('end')
        indate = request.form.get('in-date')
        # outdate = request.form.get('out-date')
        adult = request.form.get('adult')
        # child = request.form.get('child')
        print(start_add, end_add, indate, adult)
        
        # converting to IATA code for flight search
        start_calc = calc_lat_long(start_add)
        start= start_calc[3]
        start_air = start_calc[2]


        ## assuming cab fare to be rs 15 per km
        ## assuming cab travels at 30km/hr
        start_fare=start_calc[6]*15
        start_cab_time=int((start_calc[6]/30)*60)
        end_calc = calc_lat_long(end_add)
        end=end_calc[3]
        end_air = end_calc[2]
        end_fare = end_calc[6] * 15
        end_cab_time = int((end_calc[6] / 30)*60)
        print(start,end, start_calc[6],end_calc[6])


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
                max=10,

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
                        "X-RapidAPI-Key": "23f0a5b85cmsh83140e0a39e0664p11dbefjsnd7193ad7a38b",
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
            return render_template('abcd.html', start_cab_time=start_cab_time,end_cab_time=end_cab_time,start_fare=start_fare,end_fare=end_fare,start_add=start_add, end_add=end_add,start_air=start_air,end_air=end_air, flights=flights)
        except ResponseError as error:
            print(error)

    return render_template('plan.html')

@app.route('/final', methods=["GET", "POST"])
def final():
    start_add = request.args.get('start_add')
    end_add = request.args.get('end_add')
    flg= request.args.getlist('flg')
    flg=flg[0].strip('[]').split(',')
    flg=[i.strip("/"" '") for i in flg]
    start_air=request.args.get('start_air')
    end_air=request.args.get('end_air')

    start_fare=request.args.get('start_fare')
    end_fare = request.args.get('end_fare')
    start_cab_time=request.args.get('start_cab_time')
    end_cab_time=request.args.get('end_cab_time')

    print(flg)
    return render_template('final.html',start_cab_time=start_cab_time,end_cab_time=end_cab_time,start_fare=start_fare,end_fare=end_fare,start_air=start_air,end_air=end_air,flg=flg,end_add=end_add,start_add=start_add)


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


if __name__ == "__main__":
    app.run(debug=True, port=5002)