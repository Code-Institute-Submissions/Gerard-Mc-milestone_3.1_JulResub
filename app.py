import os
import requests
import json
import re
import math
from bs4 import BeautifulSoup
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
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
mongo = PyMongo(app)


@app.route('/')
def find_gpus():
    user = None
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
    return render_template("index.html", user=user)


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
    user = None
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
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
                return redirect(url_for("login"), user=user)

        else:
            # If username unuccessful, user is directed to login page
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"), user=user)
    return render_template("login.html", user=user)


@app.route("/logout")
def logout():
    if "user" in session:
        flash("Successfully logged out")
        # Removes user from session storage
        session.pop("user")
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/search_gpu", methods=["GET", "POST"])
def search_gpu():
    gpu_in_database = None
    # Search MongoDb for GPUs based on user form input
    user_gpu_update = request.form.get("user-gpu")
    if user_gpu_update:
        gpu = list(mongo.db.strong_gpu.find(
            {"model": {"$regex": user_gpu_update, "$options": "i"}}))

    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        if "gpu" in user:
            current_gpu = mongo.db.strong_gpu.find_one(
                {"model": {"$regex": user['gpu'], "$options": "i"}})
            gpu_in_database = current_gpu

    if "user" not in session:
        flash("You must log-in to view this page")
        return redirect(url_for("login"))

    if not user_gpu_update:
        if "gpu" in user:
            gpu_in_database = mongo.db.strong_gpu.find_one(
                {"model": user['gpu']})

        return redirect(url_for("profile.html"))
    return render_template(
        "profile.html", gpu=gpu, user=user, gpu_in_database=gpu_in_database)


@app.route('/submit', methods=["GET", "POST"])
def submit():
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        # Take user GPU choice from hidden text in a form
        user_gpu_model = request.form.get('hidden-text-gpu-model')
        set_gpu = {"$set": {"gpu": user_gpu_model}}
        # Creates or updates a user gpu field
        mongo.db.users.update_one(user, set_gpu)
        return redirect(url_for("profile", user=user))
    return redirect(url_for("login"))


@app.route("/profile/<user>", methods=["GET", "POST"])
def profile(user):
    gpu_in_database = None
    fps_average = None
    # Dynamically creates a user page based on session data
    if "user" in session:
        user = mongo.db.users.find_one(
            {"name": session["user"]})
        # Searches the name of the user GPU in the GPU database collection
        # to be used by Jinja logic when page loads.
        if "gpu" in user:
            gpu_in_database = mongo.db.strong_gpu.find_one(
                {"model": user['gpu']})
        # Adds the user's username and their frames-per-second input
        # to a unique object within an array called userfps.
        # This array holds FPS information from any user
        # for this specficic game and GPU configuration.
        if request.method == "POST":
            username = user['name']
            game_name = request.form.get("game-name")
            user_fps_input = request.form.get("submit_fps_input")
            # Checks and deletes if the user has already
            # inputted the FPS achieved with the game.
            mongo.db.strong_gpu.update_one(
                {'$and': [{'model': f"{gpu_in_database['model']}"}, {
                    'games.name': game_name}]}, {
                        "$pull": {"games.$.userfps": {
                            'username': username}}})
            # Adds the user's FPS input to the GPU entity.
            mongo.db.strong_gpu.update_one(
                {'$and': [{'model': f"{gpu_in_database['model']}"}, {
                    'games.name': game_name}]}, {
                        "$addToSet": {"games.$.userfps": {
                            'username': username,
                            'fps': int(user_fps_input)}}})
        # The display variable is used in the profile.html
        # JavaScript to prevent elements displaying or not displaying
        # inappropriately when the user navigates backwards on their browser.
        display = False
        if request.method == "GET":
            display = True

    if "user" not in session:
        flash("You must be logged in to view this page")
        return render_template("login.html")

        return render_template(
            "profile.html", user=user, display=display,
            gpu_in_database=gpu_in_database, fps_average=fps_average)
    return render_template("login.html")


@app.route('/search_game_homepage', methods=["GET", "POST"])
def search_game_homepage():
    query_game = request.form.get("query-game")
    game_list = []
    game = list(mongo.db.game.find(
        {"name": {"$regex": query_game, "$options": "i"}}))
    if game:
        for i in game:
            # Steam Game Ids are always a factor of 10
            # Other software can be any number. This ensures it's only games.
            if i["appid"] % 10 == 0:
                game_list.append(i)
    # Makes sure the game is not missing because of Roman numerals.
    # Eg Grand Theft Auto V
    elif not game:
        query_game = re.sub(r"1",  "I", query_game)
        query_game = re.sub(r"2",  "II", query_game)
        query_game = re.sub(r"3",  "III", query_game)
        query_game = re.sub(r"4",  "IV", query_game)
        query_game = re.sub(r"5",  "V", query_game)
        query_game = re.sub(r"6",  "VI", query_game)
        query_game = re.sub(r"7",  "VII", query_game)
        query_game = re.sub(r"8",  "VIII", query_game)
        query_game = re.sub(r"9",  "IX", query_game)
        query_game = re.sub(r"10",  "X", query_game)
        game = list(mongo.db.game.find(
            {"name": {"$regex": query_game, "$options": "i"}}))
        if game:
            for i in game:
                if i["appid"] % 10 == 0:
                    game_list.append(i)
        else:
            flash("We don't have this game in our database.")
    return render_template("index.html", game_list=game_list)


@app.route("/search_gpu_homepage", methods=["GET", "POST"])
def search_gpu_homepage():
    query_gpu = request.form.get("query-gpu")
    gpu = mongo.db.strong_gpu.find(
        {"model": {"$regex": query_gpu, "$options": "i"}})
    return render_template("index.html", gpu=gpu)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "user" in session:
        if user["name"] != "admin":
            flash("You must be Admin to view this page")
            return render_template("login.html")
        user = mongo.db.users.find_one(
            {"name": session["user"]})

    if "user" not in session:
        flash("You must be Admin to view this page")
        return render_template("login.html")

    gpus = mongo.db.strong_gpu.aggregate(
        [{"$sort": {"rating": 1}}])
    if request.method == "POST":
        insert_gpu_model = request.form.get("insert-gpu-model")
        insert_gpu_rating = request.form.get("insert-gpu-rating")
        delete_gpu_rating = request.form.get("delete-gpu-rating")

        if delete_gpu_rating:
            mongo.db.strong_gpu.delete_one(
                {"rating": int(delete_gpu_rating)})
            database_gpus = mongo.db.strong_gpu.find(
                {"rating": {"$gt": int(delete_gpu_rating)}})
            for gpu in database_gpus:
                mongo.db.strong_gpu.update_one(
                    {"model": gpu["model"], "rating": gpu["rating"]},
                    {"$set": {"rating": gpu["rating"] - 1}})

        if insert_gpu_model:
            gpu_rating_adjusted = int(insert_gpu_rating) - 1
            database_gpus = mongo.db.strong_gpu.find(
                {"rating": {"$gt": gpu_rating_adjusted}})
            for gpu in database_gpus:
                mongo.db.strong_gpu.update_one(
                    {"model": gpu["model"], "rating": gpu["rating"]},
                    {"$set": {"rating": gpu["rating"] + 1}})
            mongo.db.strong_gpu.insert_one(
                {"model": insert_gpu_model, "rating": int(insert_gpu_rating)})
        return redirect(url_for("admin", gpus=gpus, user=user))
    return render_template("admin.html", gpus=gpus, user=user)


@app.route('/check', methods=["GET", "POST"])
def check():
    # Messages to be displayed based on game being found on the API
    # and GPU being compatible or not compatible with the game.
    # info_message will be sent to the results page informing
    # the user of the result.
    info_message = None
    message_success = "Your GPU supports this game."
    message_fail = "Your GPU does not support this game."
    not_found_message = "We can't find this configuration in our database."
    not_found_message_extra = """We can't find this configuration in our database.\nTry
    reading the minimum requirements above for further information."""

    # Extract user gpu model, game id,
    # and game name from "submit_to_python" form.
    user_gpu_name = request.form.get("gpu-model")
    user_gpu_rating = int(request.form.get('gpu-rating'))
    user_game_name = request.form.get("game-name")
    user_game_id = format(request.form['game-id'])

    # Checks the user GPU in the database to see if the game
    # has been found to be already compatible from a previous search.
    check_database = mongo.db.strong_gpu.find_one(
        {'$and': [{'model': f"{user_gpu_name}"}, {'games': {
            '$elemMatch': {'name': f"{user_game_name}"}}}]})

    if check_database:
        gpu_in_database = check_database
        print("Already in database")
        return render_template(
            "result.html", user_gpu_name=user_gpu_name,
            gpu_in_database=gpu_in_database,
            user_game_name=user_game_name, info_message=message_success)

    # Below uses the user game id to connect to a specific external API file
    r = requests.get(
        f"https://store.steampowered.com/api/appdetails?appids={user_game_id}")

    # Sometimes the Steam API has missing documents and returns a json file
    # with 'success': False.
    # This seems to be from duplicate game names in the API game list.
    # Only one has the correct ID that corresponds to a link with a
    # JSON file containing the full game information.
    # Below checks for this and alerts the user that the game isn't
    # in the database and then removes the duplicate
    # or faulty game/ID from the database.
    find_missing_api_json = re.search(
        "(?<='success': False).+", str(json.loads(r.text)))
    if find_missing_api_json:
        print("--------------API Fail-----------------")
        # mongo.db.game.delete_one({ "appid": int(user_game_id) })
        return render_template("result.html", user_gpu_name=user_gpu_name,
                               user_game_name=user_game_name,
                               info_message=not_found_message)
    # Loads json data and extracts the game's PC minimum requirements.
    steam = json.loads(
        r.text)[user_game_id]['data']['pc_requirements']['minimum']

    steam_formatted = None
    gpu_requirements = None

    # Searches different variations of GPU requirements title in json data
    # to prevent issues with regex confusing normal ram with video ram sizes.
    # When title is found, regex cuts from the graphics part of the json file.
    if re.search("(?<=Graphics Card:).+", steam):
        steam_formatted = re.findall("(?<=Graphics Card:).+", steam)
    elif re.search("(?<=Graphics:).+", steam):
        steam_formatted = re.findall("(?<=Graphics:).+", steam)
    elif re.search("(?<=Video Card:).+", steam):
        steam_formatted = re.findall("(?<=Video Card:).+", steam)
    elif re.search("(?<=Video:).+", steam):
        steam_formatted = re.findall("(?<=Video:).+", steam)
    # For the rare occasion when the JSON is in Russian
    elif re.search("(?<=Видеокарта:).+", steam):
        steam_formatted = re.findall("(?<=Видеокарта:).+", steam)

    if steam_formatted:
        steam_has_been_formatted = True
        steam_formatted = str(steam_formatted)
        # Cuts the json at the end of the graphics section.
        # The Graphics, CPU, HDD, Sound, etc. elements always end with </li>.
        steam_formatted = re.sub(r"<\/li>.*$", "", steam_formatted)

    else:
        steam_has_been_formatted = False

    '''
    All GPUs that the user has an option to select are above
    1GB VRAM and have a higher frequency, floating point operations per second,
    more power, later DirectX capability, etc., than any older GPUs that have
    VRAM of 512MB and below(according to wikipedia).
    If the first regex pattern below finds vram requirements of 512mb or below
    in the Steam api,the function ends and the user receives a success message.
    These avoids unnecessarily searching the database
    and comparing user/requirements GPUs.
    '''
    # Find old gpus under 512mb
    if steam_has_been_formatted is True:
        old_gpu = re.findall(r"(?i)(?:\d+\sMB|\d+MB)", steam_formatted)
        if old_gpu:
            for match in old_gpu:
                if re.search(r'(?i)(?:1024\s*mb|2048\s*mb|4096\s*mb)', match):
                    pass
                else:
                    info_message = message_success
                    print("Found GPU under 512mb")

    gpu_requirements = steam

    # Fix Steam Nvidia naming inconsistencies to align with this app's database
    # Eg. Geforce 7800GTX > Geforce 7800 GTX or Nvidia 7800GT > Geforce 7800 GT
    if info_message != message_success:
        find_gtx_gt_fix = re.findall(
            r'(?i)(?:nvidia\sgeforce|nvidia|geforce)\s\d+gt[xX]?\s',
            gpu_requirements)
        if find_gtx_gt_fix:
            for i in find_gtx_gt_fix:
                before = i
                i = re.sub(r"(?i)nvidia\sgeforce",  "", i)
                i = re.sub(r"(?i)nvidia",  "", i)
                i = re.sub(r"(?i)geforce\s",  " ", i)
                i = re.sub(r"^\s",  "Nvidia GeForce ", i)
                a = re.sub(
                    r"(?i)(?:GTX|GT)", lambda ele: " " + ele[0] + " ", i)
                switch = a
                gpu_requirements = re.sub(before,  switch, gpu_requirements)
            print("Found gt/gtx format error")

    """ The below regex patterns find AMD and Nvidia GPUs that are below the power
    of the weakest GPU the user can choose from. If any of these patterns are
    matched, the user info message will be success. """

    # Find Nvidia gpus. Geforce 256 - geforce 8000 series. Years 1999-2008.
    if info_message != message_success:
        find_old_geforce_gpu = re.findall(
            r'(?i)(?:(?:nvidia\s|geforce\s)(?:256|fx|pcx|mx4000|8\d{3}|6\d{3}'
            r'|7\d{3}(?!m))|geforce[2-4]{1}\s)', gpu_requirements)
        if find_old_geforce_gpu:
            info_message = message_success
            print("Found older Nvidia GPU")

    # # Find AMD GPU Radeon 8000 series - HD 3000 series. Years 2001-2008
    if info_message != message_success:
        find_old_amd_gpu = re.findall(
            r'(?i)(?:3d\srage|rage\s(?:pro|xl|128|fury)'
            r'|(?:radeontm\s|ati\s|amd\s|radeon\s)(?:ve|le|sdr|ddr'
            r'|7500|3[2-4]{1}0|[8-9]\d{3,4}|x\d{3,4}|hd\s[2-3]\d{3}))',
            gpu_requirements)
        if find_old_amd_gpu:
            info_message = message_success
            print("Found older AMD GPU")

    ''' The below code will find any patterns that are for GPUs not guaranteed
    to be less powerful than the user GPU.
    They will find the patterns in the Steam API game information .json files
    and search MongoDB to find a match.
    If it finds a match, it will compare the GPU rating field of both the users
    GPU and the GPU on in the API json.
    If the user gpu is a higher rating, they receive a success message.
    '''
    # Find intel integrated graphics cards
    # eg. intel hd 3000 and Intel hd 620
    if info_message != message_success:
        find_intel_gpu = re.findall(
            r'(?i)(?!Amd|Radeon)(?:intel\s)'r'(?:u?hd|'
            r'(?:iris\s(?:pro|plus|xe\smax|xe))|iris)(?:\sgraphics\s|\s)'
            r'(?:\d+[a-zA-Z]{0,2}|xe|g[1-7]'
            r'|(?:\d{2}(?:\s*eus*)))*\s*(?:graphics'
            r'|(?:\d{2}(?:\s*eus*))|$)*(?:\(laptop\)|laptop|\(mobile\)|mobile'
            r'|\(m\)|m|\(notebook\)|notebook)*', gpu_requirements)
        if find_intel_gpu:
                for gpu in find_intel_gpu:
                    gpu = re.sub(r"(?i)graphics",  "", gpu)
                    gpu = re.sub(r"(?i)eus",  "eu", gpu)
                    gpu = re.sub(r"(?i)\s\s",  " ", gpu)
                    gpu = re.sub(r"(?i)^\s",  "", gpu)
                    gpu = re.sub(
                        r"(?i)(?:\(laptop\)|laptop|\(Notebook\)"
                        r"|Notebook|\(m\))", "Mobile", gpu)
                    gpu = re.sub(r"(?i)(?:\sm\s|\sm$)",  " Mobile", gpu)
                    gpu = re.sub(r"(?i)\s$",  "", gpu)
                    gpu = re.sub(r"(?i)\s\s$",  "", gpu)
                    gpu = re.sub(r"(?i)[)(]",  "", gpu)
                    # Intel GPUs stronger than the weakest
                    # intel GPU available for user selection.
                    check_strong_gpu = mongo.db.strong_gpu.find(
                        {"model": {"$regex": gpu, "$options": "i"}})
                    in_gpu = False
                    if check_strong_gpu:
                        for object in check_strong_gpu:
                            if str(object["model"]) == str(gpu):
                                in_gpu = True
                                # Compares the GPU rating against the user GPU
                                if user_gpu_rating <= object["rating"]:
                                    info_message = message_success
                                    break
                                elif user_gpu_rating > object["rating"]:
                                    info_message = message_fail
                                    break

                    if in_gpu is False:
                        find_strong_intel_gpus = re.findall(
                            r'(?i)(?:(?:u?hd|iris)\s'
                            r'((?:630|620|530|520|540|'
                            r'550|6000|5600|xe|plus|pro)(?:\s|$)))', gpu)
                        if not find_strong_intel_gpus:
                            check_weaker_gpu = mongo.db.weaker_gpu.find(
                                {"model": {"$regex": gpu, "$options": "i"}})
                            if check_weaker_gpu:
                                for object in check_weaker_gpu:
                                    if str(object["model"]) == str(gpu):
                                        info_message = message_success
                                        print("Found WEAK SUCCESS")

                    if info_message == message_success:
                        break

    # Find post 2008 Nvidia GPUs.
    if info_message != message_success:
        find_newer_gtx_gpu = re.findall(
            r'(?i)(?:nvidia\sgeforce\s|geforce\s|nvidia\s|gtx\s'
            r'|gt\s|rtx\s|gts\s|geforce\sg|mx|geforce\sm)(?:\d+\s*-*\d+gb'
            r'|\d*[a-zA-Z]*\s*\d*\s*)(?:max-q|NotebookR|max\sq|\(max\sq\)'
            r'|\(max-q\)|max\sq|ti\sboost|ti|le|super\smax-q'
            r'|se|super|\d+m|\(laptop\)|laptop|\(mobile\)|mobile'
            r'|\(m\)|m|\(notebook\)|notebook|\(notebook\srefresh\)'
            r'|\(\d+watts\)|\d+watts|\(\d+w\)|\d+w)*(?:\smax-q'
            r'|\smax\sq|\s\(max\sq\)|\s\(max-q\)|\s\(*mobile\)*|\s\(*m\)*'
            r'|\s\(laptop\)\slaptop|\sNotebookR'
            r'|\s\(notebook\srefresh\)|\snotebook\srefresh|\s\(notebook\)'
            r'|\snotebook|-\d+gb|\s\d+gb|\d+\sgb'
            r'|\s\(refresh\)|\srefresh||\s\(\d+watts\)|\s\d+watts'
            r'|\s\(\d+w\)|\s\d+w)*', gpu_requirements)
        if find_newer_gtx_gpu:
            for gpu in find_newer_gtx_gpu:
                # Formats string to be compatible with database
                gpu = re.sub(r"(?i)Nvidia",  "", gpu)
                gpu = re.sub(r"(?i)GeForce",  "", gpu)
                gpu = re.sub(r"\s\s",  " ", gpu)
                gpu = re.sub(r"^\s",  "", gpu)
                gpu = re.sub(r"\s\s$",  "", gpu)
                gpu = re.sub(r"\s$",  "", gpu)
                gpu = re.sub(r"^",  "NVIDIA GeForce ", gpu)
                gpu = re.sub(
                    r'(?i)(?:\(laptop\srefresh\)|laptop\srefresh'
                    r'|\(mobile\srefresh\)|mobile\srefresh|\(m\srefresh\)'
                    r'|m\srefresh|\(notebook\srefresh\)|\snotebook\srefresh)',
                    "NotebookR", gpu)
                gpu = re.sub(
                    r"(?i)(?:\(laptop\)$|laptop$|\(mobile\)$|mobile$"
                    r"|\(m\)$)",  "Notebook", gpu)
                gpu = re.sub(r"(?i)(?:\sm$)",  " Notebook", gpu)
                gpu = re.sub(r"[)(]",  "", gpu)
                gpu = re.sub(r"(?i)(?:watts|watts$)",  "w", gpu)
                gpu = re.sub(r"\s\s",  " ", gpu)
                check_strong_gpu = mongo.db.strong_gpu.find(
                    {"model": {"$regex": "^" + gpu + "$", "$options": "i"}})
                in_gpu = False
                if check_strong_gpu:
                    for object in check_strong_gpu:
                        if str(object["model"]) == str(gpu):
                            # Compares the GPU rating against the user's GPU
                            if user_gpu_rating <= object["rating"]:
                                print("NVIDIA STRONG SUCCESS")
                                in_gpu = True
                                info_message = message_success

                            elif user_gpu_rating > object["rating"]:
                                print("NVIDIA STRONG Fail")
                                info_message = message_fail

                if in_gpu is False:
                    gpu = re.sub(r"NVIDIA\sGeForce",  "GeForce", gpu)
                    check_weaker_gpu = mongo.db.weaker_gpu.find(
                        {"model": {"$regex": gpu, "$options": "i"}})
                    if check_weaker_gpu:
                        for object in check_weaker_gpu:
                            if str(object["model"]) == str(gpu):
                                info_message = message_success

                if info_message == message_success:
                    break

    # Find Nvidia titan GPUs
    if info_message != message_success:
        find_nvidia_titan = re.findall(
            r'(?i)(?:geforce\sgtx\stitan|nvidia\sgtx\stitan'
            r'|nvidia\stitan|titan)\s(?:rtx|gtx|X\s'
            r'\(?Pascal\)?|Xp\sCollector\'s\sEdition|xp|x|V|5|black)',
            gpu_requirements)
        if find_nvidia_titan:
            for gpu in find_nvidia_titan:
                gpu = re.sub(r"^\s",  "", gpu)
                gpu = re.sub(r"\s\s$",  "", gpu)
                gpu = re.sub(r"\s$",  "", gpu)
                gpu = re.sub(r"  ",  " ", gpu)
                check_strong_gpu = mongo.db.strong_gpu.find(
                    {"model": {"$regex": "^" + gpu + "$", "$options": "i"}})
                if check_strong_gpu:
                    for object in check_strong_gpu:
                        if str(object["model"]) == str(gpu):
                            # Compares the GPU rating against the user's GPU
                            if user_gpu_rating <= object["rating"]:
                                print("NVIDIA Titan SUCCESS")
                                info_message = message_success
                                break
                            elif user_gpu_rating > object["rating"]:
                                print("NVIDIA Titan Fail")
                                info_message = message_fail
                                break

                if info_message == message_success:
                    break

    # Find Nvidia Quadro GPUs
    if info_message != message_success:
        find_nvidia_quadro = re.findall(
            r'(?i)(?:quadro\srtx|rtx|quadro\snvs|nvs'
            r'|quadro[2-4]|quadro\sfx|quadro)\s(?:plex\s\d{3,4}'
            r'|k*m*g*v*p*a*t*\d{3,4}d*m*|cx|ddr|mxr|ex|pro|dcc|\d{3}xgl'
            r'|fx\s\d{3,4}g*x*2*(?:\ssdi|\slp|)|fx\s\d{3,4}'
            r'|\d{2})*\s*(?:go\d{3,4}|go\sgl|go|max-q)*',
            gpu_requirements)
        if find_nvidia_quadro:
            for gpu in find_nvidia_quadro:
                gpu = re.sub(r"^\s",  "", gpu)
                gpu = re.sub(r"\s\s$",  "", gpu)
                gpu = re.sub(r"\s$",  "", gpu)
                gpu = re.sub(r"  ",  " ", gpu)
                gpu = re.sub(r"^",  "NVIDIA GeForce ", gpu)
                check_strong_gpu = mongo.db.strong_gpu.find(
                    {"model": {"$regex": "^" + gpu + "$", "$options": "i"}})
                in_gpu = False
                if check_strong_gpu:
                    for object in check_strong_gpu:
                        if str(object["model"]) == str(gpu):
                            # Compares the GPU rating against the user's GPU
                            if user_gpu_rating <= object["rating"]:
                                print("NVIDIA Quadro STRONG SUCCESS")
                                in_gpu = True
                                info_message = message_success

                            elif user_gpu_rating > object["rating"]:
                                print("NVIDIA Quadro STRONG Fail")
                                info_message = message_fail

                if in_gpu is False:
                    gpu = re.sub(r"NVIDIA\sGeForce ",  "", gpu)
                    check_weaker_gpu = mongo.db.weaker_gpu.find(
                        {"model": {"$regex": gpu, "$options": "i"}})
                    if check_weaker_gpu:
                        for object in check_weaker_gpu:
                            if str(object["model"]) == str(gpu):
                                info_message = message_success

                if info_message == message_success:
                    break

    # Finds newer AMD GPUs
    if info_message != message_success:
        find_new_amd_gpu = re.findall(
            r'(?i)(?:mobility\sradeon|radeon|amd)'
            r'\s(?:VII|hd|rx|r[5-9]|x*\d{3,4}x*)\s*(?:m*\d{3,4}d*x*v*m*g*'
            r'|fury|vega)*\s*(?:X2|Graphics|XT|X|56|64|Pro)*',
            gpu_requirements)
        if find_new_amd_gpu:
            for gpu in find_new_amd_gpu:
                store_name = gpu
                # Formats String to be compatible with database
                gpu = re.sub(r"(?i)ati",  "", gpu)
                gpu = re.sub(r"(?i)amd",  "", gpu)
                gpu = re.sub(r"(?i)radeon",  "", gpu)
                gpu = re.sub(r"^",  "AMD Radeon ", gpu)
                gpu = re.sub(r"\s\s",  " ", gpu)
                gpu = re.sub(r"\s\s$",  "", gpu)
                gpu = re.sub(r"\s$",  "", gpu)
                check_strong_gpu = mongo.db.strong_gpu.find(
                    {"model": {"$regex": "^" + gpu + "$", "$options": "i"}})
                in_gpu = False
                if check_strong_gpu:
                    for object in check_strong_gpu:
                        if str(object["model"]) == str(gpu):
                            # Compares the GPU rating against the user's GPU
                            if user_gpu_rating <= object["rating"]:
                                print("AMD STRONG SUCCESS")
                                print(gpu)
                                in_gpu = True
                                info_message = message_success
                                break

                            elif user_gpu_rating > object["rating"]:
                                print("AMD STRONG Fail")
                                info_message = message_fail
                                break
                    gpu = re.sub(r"AMD ",  "", gpu)
                    gpu = re.sub(r"ATI ",  "", gpu)
                    check_weaker_gpu = mongo.db.weaker_gpu.find(
                        {"model": {"$regex": gpu, "$options": "i"}})
                    if check_weaker_gpu:
                        for object in check_weaker_gpu:
                            if str(object["model"]) == str(gpu):
                                print("AMD Weak Success")
                                print(str(gpu))
                                info_message = message_success
                                break

                if info_message == message_success:
                    break

    # If GPU is found to be strong enough, the users inputed game
    # is added to an array that stores a list of compatible games
    #  within the GPU entity in the database.
    if info_message == message_success:
        print("here")
        mongo.db.strong_gpu.update_one(
                {"model": user_gpu_name},
                {"$push": {'games': {"name": user_game_name}}})
        print(user_gpu_name)
        print(user_game_name)
        print("Added to database")

    else:
        info_message = not_found_message_extra

    return render_template(
        "result.html", user_gpu_name=user_gpu_name,
        user_game_id=user_game_id,
        user_game_name=user_game_name, steam=steam,
        info_message=info_message)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
