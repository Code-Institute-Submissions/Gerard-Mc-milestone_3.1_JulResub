import os
from bson import ObjectId
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for, jsonify)
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env

app = Flask(__name__)
app.config["MONGO_DBNAME"] = 'os.environ.get("MONGO_DBNAME")'
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")
mongo = PyMongo(app)


# Test #
@app.route('/')
def find_gpus():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # View for user registration
    if request.method == "POST":
        # Search mongo to match entered username
        existing_user = mongo.db.users.find_one(
            {"name": request.form.get("username").lower()})

        if existing_user:
            # If username found, user is alerted with a flash message
            flash("Username is not available")
            return redirect(url_for("register"))
        # If username available, new user dictionary created
        new_user = {
            "name": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        # Dictionary added to database
        mongo.db.users.insert_one(new_user)
        flash(f"Welcome aboard {new_user['name']}!")
        # User is added to session data
        session["user"] = new_user['name']
        return redirect(url_for("profile", user=session["user"]))
    # If username unavailable, register page is loaded
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        # Searches database for the entered username
        existing_user = mongo.db.users.find_one(
            {"name": request.form.get("username").lower()})

        if existing_user:
            # If username exists, entered password is checked againgst the database user entity
            if check_password_hash(existing_user["password"],
                                   request.form.get("password")):
                # If successful, session data updated and user is directed to profile page
                session['user'] = existing_user['name']
                return redirect(url_for("profile", user=session['user']))
            else:
                # If password unuccessful, user is directed to login page
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # If username unuccessful, user is directed to login page
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    flash("Successfully logged out")
    # Removes user from session storage
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/search_gpu", methods=["GET", "POST"])
def search_gpu():
    # Search MongoDb for GPUs based on user form input
    user_gpu = request.form.get("user-gpu")
    gpu = list(mongo.db.gpu.find(
        {"$text": {"$search": "\"" + user_gpu + "\""}}))
    user = mongo.db.users.find_one(
        {"name": session["user"]})
    return render_template("profile.html", gpu=gpu, user=user)


@app.route('/submit', methods=["GET", "POST"])
def submit():
    user = mongo.db.users.find_one(
        {"name": session["user"]})
    # Take user GPU choice from hidden text in a form
    user_gpu_model = request.form.get('hidden-text-gpu-model')
    set_gpu = {"$set": {"gpu": user_gpu_model}}
    # Creates or updates a user gpu field
    mongo.db.users.update_one(user, set_gpu)
    return redirect(url_for("profile", user=user))


@app.route("/profile/<user>", methods=["GET", "POST"])
def profile(user):
    # Dynamically creates a user page based on session data
    user = mongo.db.users.find_one(
        {"name": session["user"]})
    return render_template("profile.html", user=user)


@app.route('/search_game_homepage', methods=["GET", "POST"])
def search_game_homepage():
    query = request.form.get("query")
    game_list = []
    game = list(mongo.db.game.find(
        {"$text": {"$search": "\"" + query + "\""}}))
    for i in game:
        if i["appid"] % 10 == 0:
            game_list.append(i)
    print(game)
    return render_template("index.html", game_list=game_list)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
