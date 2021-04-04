import os
import requests
import json
import re
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
            # If username exists, entered password is checked
            # againgst the database user entity
            if check_password_hash(existing_user["password"],
                                   request.form.get("password")):
                # If successful, session data updated and user
                # is directed to profile page
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


@app.route("/search_gpu_homepage", methods=["GET", "POST"])
def search_gpu_homepage():
    query_gpu = request.form.get("query-gpu")
    gpu = list(mongo.db.gpu.find(
        {"$text": {"$search": "\"" + query_gpu + "\""}}))
    return render_template("index.html", gpu=gpu)


@app.route('/check', methods=["GET", "POST"])
def check():
    # Messages to be displayed based on game being found on the API
    # and GPU being compatible or not compatible with the game.
    # info_message will be sent to the results page informing
    # the user of the result.
    info_message = ""
    message_success = "Your GPU supports this game"
    message_fail = "Your GPU does not support this game"
    message_not_found = "We can't find this configuration in our database"

    # Extract user gpu model, game id,
    # and game name from "submit_to_python" form.
    user_gpu_name = request.form.get("gpu-model")
    user_game_name = request.form.get("game-name")
    user_game_id = format(request.form['game-id'])
    # Below uses the user game id to connect to a specific external API file
    r = requests.get(
        f"https://store.steampowered.com/api/appdetails?appids={user_game_id}")
    # Sometimes the external API has issues with it's own game ids.
    # In that case, the below sends an error message to the result page.
    if not r:
        steam = message_not_found
        return render_template("result.html", user_gpu_name=user_gpu_name,
                               user_game_name=user_game_name, steam=steam)
    # Loads json data and extracts the game's PC minimum requirements.
    steam = json.loads(
        r.text)[user_game_id]['data']['pc_requirements']['minimum']

    # Searches different variations of GPU requirements title in json data.
    # to prevent issues with regex confusing normal ram with video ram sizes.
    find_title_is_graphics = re.search("(?<=Graphics:).+", steam)
    find_title_is_video = re.search("(?<=Video:).+", steam)
    find_title_is_graphics_card = re.search("(?<=Graphics Card:).+", steam)
    find_title_is_video_card = re.search("(?<=Video Card:).+", steam)
    find_title_is_russian = re.search("(?<=Видеокарта:).+", steam)
    # Finds section when there is html in between the title and it's
    #  following colon. (Happens rarely)
    find_title_is_graphics_card_no_colon = re.search(
        "(?<=Graphics Card).+", steam)
    find_title_is_graphics_no_colon = re.search("(?<=Graphics).+", steam)
    find_title_is_video_card_no_colon = re.search("(?<=Video Card).+", steam)
    find_title_is_video_no_colon = re.search("(?<=Video).+", steam)
    find_title_is_russian_no_colon = re.search("(?<=Видеокарта).+", steam)

    # When title is found, regex cuts from the graphics part of the json file.
    if find_title_is_graphics:
        gpu_requirements = re.findall("(?<=Graphics:).+", steam)
    elif find_title_is_graphics_card:
        gpu_requirements = re.findall("(?<=Graphics Card:).+", steam)
    elif find_title_is_video:
        gpu_requirements = re.findall("(?<=Video:).+", steam)
    elif find_title_is_video_card:
        gpu_requirements = re.findall("(?<=Video Card:).+", steam)
    elif find_title_is_russian:
        gpu_requirements = re.findall("(?<=Видеокарта:).+", steam)
    # Regex cuts from the graphics when there is html in between the title and it's following colon.
    elif find_title_is_graphics_no_colon:
        gpu_requirements = re.findall("(?<=Graphics).+", steam)
    elif find_title_is_graphics_card_no_colon:
        gpu_requirements = re.findall("(?<=Graphics Card).+", steam)
    elif find_title_is_video_card_no_colon:
        gpu_requirements = re.findall("(?<=Video Card).+", steam)
    elif find_title_is_video_no_colon:
        gpu_requirements = re.findall("(?<=Video).+", steam)
    elif find_title_is_russian_no_colon:
        gpu_requirements = re.findall("(?<=Видеокарта).+", steam)
    # When the graphics section can't be found, the info message
    else:
        gpu_requirements = ""
        info_message = message_not_found
    # Tidy gpu_requirements variable data for easier regex use.
    if gpu_requirements != "":
        # Removes words that will conflict or complicate regex patterns
        # and removes extra html.
        gpu_requirements_cut = re.sub(
            "(?i)(?:series\s|or\s|better\s|<\/strong>|<br>|:)", "", gpu_requirements[0])
        # Cuts the json at the end of the graphics section. The Graphics, CPU, HDD, Sound etc always end with </li>.
        gpu_requirements = re.sub("<\/li>.*$", "", gpu_requirements_cut)

    '''  Below fixes naming inconsistancies found in the Steam API files for Nvidia GPUs '''
    # Fix Steam Nvidia naming inconsistencies to align with this app's database
    # Eg. Geforce 7800GTX -> Geforce 7800 GTX or Nvidia 7800GT -> Geforce 7800 GT
    find_gtx_gt_fix = re.findall(
        '(?i)(?:nvidia\sgeforce|nvidia|geforce)\s\d+gt[xX]?\s', gpu_requirements)
    for i in find_gtx_gt_fix:
        before = i
        i = re.sub("(?i)nvidia\sgeforce",  "", i)
        i = re.sub("(?i)nvidia",  "", i)
        i = re.sub("(?i)geforce\s",  " ", i)
        i = re.sub("^\s",  "Nvidia GeForce ", i)
        a = re.sub("(?i)(?:GTX|GT)", lambda ele: " " + ele[0] + " ", i)
        switch = a
        gpu_requirements = re.sub(before,  switch, gpu_requirements)

    '''
    Because all user GPUs are above 1GB VRAM,
    and only older GPU's VRAM is measured in MB, 512MB and below.
    If the first regex pattern below finds these, it returns a success message
    because the GPU is certain to be weaker than the users.
    '''
    # Find old gpus under 1GB
    old_gpu = re.findall("\d+MB|\d+\sMB", gpu_requirements)
    #if old_gpu:
        #info_message = message_success

    '''
    The below regex patterns find AMD and Nvidia GPUs that are below the power
    of the weakest GPU the user can choose. If any of these patterns are matched,
    the user info message will be success.
    '''

    #Find old geforce gpus. Geforce 256, geforce2, geforce3, geforce4, geforce fx, geforce 6000, geforce 7000, geforce 8000, geforce 9000 series.
    find_old_geforce_gpu = re.findall(
        "(?i)(?:nvidia\sgeforce|NVIDIA|geforce\d*)\s(?:(?:ti|mx|pcx)\d+|fx|pcx|\d+|\d+\s\+|\d+a|\d+pv)\s*(?:\d+gtx\+|gtx|gso|gt|gx2|ge|gs|le|se|mgpu|ultra|TurboCache|nForce\s4[1-3]0)*\s(?:ultra)*", gpu_requirements)
    if find_old_geforce_gpu:
        info_message = message_success
    return render_template("result.html", user_gpu_name=user_gpu_name, user_game_id=user_game_id,
                           user_game_name=user_game_name, steam=steam, gpu_requirements=gpu_requirements, info_message=info_message)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
