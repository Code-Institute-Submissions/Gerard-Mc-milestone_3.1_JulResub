import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
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
    gpus = mongo.db.gpu.find()
    return render_template("index.html", gpus=gpus)


#
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"name": request.form.get("username").lower()})

        if existing_user:
            flash("Username is not available")
            return redirect(url_for("register"))

        new_user = {
            "name": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password"))
        }
        mongo.db.users.insert_one(new_user)
        flash(f"Welcome aboard {new_user['name']}!")
        session["user"] = new_user['name']
        return redirect(url_for("profile", user=session["user"]))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"name": request.form.get("username").lower()})

        if existing_user:
            if check_password_hash(existing_user["password"],
                                   request.form.get("password")):
                session['user'] = existing_user['name']
                return redirect(url_for("profile", user=session['user']))
            else:
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    flash("Successfully logged out")
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
    mongo.db.users.update_one(user, set_gpu)
    return redirect(url_for("profile", user=user))


@app.route("/profile/<user>", methods=["GET", "POST"])
def profile(user):
    user = mongo.db.users.find_one(
        {"name": session["user"]})
    return render_template("profile.html", user=user)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
