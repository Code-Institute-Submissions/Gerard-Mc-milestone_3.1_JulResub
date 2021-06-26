import os
import requests
import json
import re
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
    if "user" in session:
        flash("Successfully logged out")
        # Removes user from session storage
        session.pop("user")
        return redirect(url_for("login"))
    return render_template("index.html")


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
        # Searches the name of the user GPU in the GPU database collection to be used
        # by Jinja logic when page loads.
        if "gpu" in user:
            gpu_in_database = mongo.db.gpu.find_one({"model": user['gpu']})
        # Adds the user's username and their frames-per-second input
        # to a unique object within an array called userfps.
        # This array holds FPS information from any user
        # for this specficic game and GPU configuration.
        if request.method == "POST":
            username = user['name']
            game_name = request.form.get("game-name")
            user_fps_input = request.form.get("submit_fps_input")
            # Checks and deletes if the user has already inputted the FPS achieved with the game.
            mongo.db.gpu.update_one(
                {'$and': [{'model': f"{gpu_in_database['model']}"}, {
                    'games.name': game_name}]}, {
                        "$pull": {"games.$.userfps": {
                            'username': username}}})
            # Adds the user's FPS input to the GPU entity.
            mongo.db.gpu.update_one(
                {'$and': [{'model': f"{gpu_in_database['model']}"}, {
                    'games.name': game_name}]}, {
                        "$addToSet": {"games.$.userfps": {
                            'username': username,
                            'fps': int(user_fps_input)}}})
        # The display variable is used in the profile.html JavaScript to prevent elements displaying
        # or not displaying inappropriately when the user navigates backwards on their browser.
        display = False
        if request.method == "GET":
            display=True
        return render_template("profile.html", user=user, display=display, gpu_in_database=gpu_in_database, fps_average = fps_average)
    return render_template("login.html")


@app.route('/search_game_homepage', methods=["GET", "POST"])
def search_game_homepage():
    query_game = request.form.get("query-game")
    game_list = []
    game = list(mongo.db.game.find(
        {"$text": {"$search": "\"" + query_game + "\""}}))
    for i in game:
        if i["appid"] % 10 == 0:
            game_list.append(i)
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
    not_found_message = "We can't find this configuration in our database"
    steam_format_error_message = """We can't find this configuration in our database.\nTry 
    reading the minimum requirements above for further information."""

    # Extract user gpu model, game id,
    # and game name from "submit_to_python" form.
    user_gpu_name = request.form.get("gpu-model")
    user_gpu_rating = int(request.form.get('gpu-rating'))
    user_game_name = request.form.get("game-name")
    user_game_id = format(request.form['game-id'])
    # Below uses the user game id to connect to a specific external API file
    r = requests.get(
        f"https://store.steampowered.com/api/appdetails?appids={user_game_id}")
    # Sometimes the Steam API has missing documents and returns a json file
    # with 'success': False.
    # This seems to be from duplicate game names in the API game list.
    # Only one has the correct ID that corresponds to a link with a JSON file containing
    # the full game information.
    # Below checks for this and alerts the user that the game isn't in the database
    # and then removes the duplicate or faulty game/ID from the database.
    find_missing_api_json = re.search(
        "(?<='success': False).+", str(json.loads(r.text)))
    if find_missing_api_json:
        print("--------------API Fail-----------------")
        mongo.db.game.delete_one({ "appid": int(user_game_id) })

        return render_template("result.html", user_gpu_name=user_gpu_name,
                               user_game_name=user_game_name,
                               info_message=not_found_message)
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
    # Regex cuts from the graphics when there is html in
    # between the title and it's following colon.
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
    # Tidy gpu_requirements variable data for easier regex use.
    if gpu_requirements != "":
        # Removes words that will conflict or complicate regex patterns
        # and removes extra html.
        gpu_requirements_cut = re.sub(
            r"(?i)(?:series\s|or\s|better\s|<\/strong>|<br>|:)", "",
            gpu_requirements[0])
        # Cuts the json at the end of the graphics section.
        # The Graphics, CPU, HDD, Sound etc always end with </li>.
        gpu_requirements = re.sub(r"<\/li>.*$", "", gpu_requirements_cut)

    else:
        info_message = steam_format_error_message
        return render_template(
        "result.html", user_gpu_name=user_gpu_name,user_game_id=user_game_id,
        user_game_name=user_game_name, steam=steam, info_message=info_message)

    '''
    Because all user GPUs are above 1GB VRAM,
    and only older GPU's VRAM is measured in MB, 512MB and below.
    If the first regex pattern below finds these, it returns a success message
    because the GPU is certain to be weaker than the users.
    '''
    # # Find old gpus under 1GB
    # old_gpu = re.findall(r"\d+MB|\d+\sMB", gpu_requirements)
    # if old_gpu:
    #     info_message = message_success

    # '''
    # Below fixes naming inconsistancies found
    # in the Steam API files for Nvidia GPUs
    # '''
    # # Fix Steam Nvidia naming inconsistencies to align with this app's database
    # # Eg. Geforce 7800GTX > Geforce 7800 GTX or Nvidia 7800GT > Geforce 7800 GT
    # find_gtx_gt_fix = re.findall(
    #     r'(?i)(?:nvidia\sgeforce|nvidia|geforce)\s\d+gt[xX]?\s',
    #     gpu_requirements)
    # if find_gtx_gt_fix:
    #     for i in find_gtx_gt_fix:
    #         before = i
    #         i = re.sub(r"(?i)nvidia\sgeforce",  "", i)
    #         i = re.sub(r"(?i)nvidia",  "", i)
    #         i = re.sub(r"(?i)geforce\s",  " ", i)
    #         i = re.sub(r"^\s",  "Nvidia GeForce ", i)
    #         a = re.sub(r"(?i)(?:GTX|GT)", lambda ele: " " + ele[0] + " ", i)
    #         switch = a
    #         gpu_requirements = re.sub(before,  switch, gpu_requirements)
    # else:
    #     pass

    # 
    """ The below regex patterns find AMD and Nvidia GPUs that are below the power
    of the weakest GPU the user can choose from. If any of these patterns are
    matched, the user info message will be success. """

    # Find old geforce gpus. Geforce 256, geforce2 - geforce4, geforce fx
    # geforce 6000, geforce 7000, geforce 8000 series.
    
    # find_old_geforce_gpu = re.findall(
    #     r'(?i)(?:geforce\s(?:256|fx|pcx|mx4000|8\d{3}|6\d{3}'
    #     r'|7\d{3}(?!m))|geforce[2-4]{1}\s)', gpu_requirements)
    # if find_old_geforce_gpu:
    #     info_message = message_success
    #     mongo.db.gpu.update_one(
    #         {"model": user_gpu_name},
    #         {"$push": {'games': {"name": user_game_name}}})
    #     print("Added to database")
    #     return render_template(
    #     "result.html", user_gpu_name=user_gpu_name,
    #     user_game_id=user_game_id,
    #     user_game_name=user_game_name, steam=steam, info_message=info_message)

    # Finds AMD GPU years 2001-2008 or from Radeon 8000 series - HD 3000 series
    # Eg. Radeon X700, Radeon X1300 XT, Radeon X1900 GT, Radeon HD 2900 PRO
    # r'(?i)(?:radeon|ati|amd)\s'
    #     r'(?:hd|x\d+|xpress\s\d+|xpress|8\d+|9\d+)\s'
    #     r'(?:[2-3]\d+\s(?:pro|xt|gt|x2|\d+)*'
    #     r'|[1-2]\d+|x\d+|le|pro|se|xt|xxl|xl|agp|gto|gt|x)', find)

    # find_old_amd_gpu = re.findall(
    #     r'(?i)(?:3d\srage|rage\s(?:pro|xl|128|fury)'
    #     r'|radeontm\s|ati\s|amd\s|radeon\s(?:ve|le|sdr|ddr'
    #     r'|7500|3[2-4]{1}0|[8-9]\d{3,4}|x\d{3,4}|hd\s[2-3]\d{3}))', gpu_requirements)
    # if find_old_amd_gpu:
    #     info_message = message_success
    #     return render_template(
    #     "result.html", user_gpu_name=user_gpu_name, user_game_id=user_game_id,
    #     user_game_name=user_game_name, steam=steam, info_message=info_message)


    ''' The below code will find any patterns that are for GPUs not guaranteed
    to be less powerful than the user GPU.
    They will find the patterns in the Steam API json and search
    MongoDB to find a match.
    If it finds a match, it will compare the GPU rating field of both the users
    GPU and the GPU on in the API json.
    If the user gpu is a higher rating, they receive a success message.
    '''
    # Find intel integrated graphics cards
    # eg. intel hd 3000 and Intel hd 620

    # with open("static/data/intel_wiki.html") as wiki:
    #     soup = BeautifulSoup(wiki, "html.parser")
    #     gpu_requirements = str(soup)

    # find_intel_gpu = re.findall(r'(?i)(?!Amd|Radeon)(?:intel\s|\s|^)*'
    # r'(?:u?hd|(?:iris\s(?:pro|plus|xe\smax|xe|))|iris)(?:\sgraphics\s|\s)'
    # r'(?:\d+[a-zA-Z]{0,2}|xe|g[1-7]|(?:\d{2}(?:\s*eus*)))*\s*(?:graphics|(?:\d{2}(?:\s*eus*))|$)*', gpu_requirements)
    # found_gpus = ""
    # if find_intel_gpu:
    #         for gpu in find_intel_gpu:
    #             print(gpu)
    #             store_name = gpu
    #             gpu = re.sub(r"(?i)graphics",  "", gpu)
    #             gpu = re.sub(r"(?i)eus",  "eu", gpu)
    #             gpu = re.sub(r"(?i)\s\s",  " ", gpu)
    #             gpu = re.sub(r"(?i)^\s",  "", gpu)
    #             gpu = re.sub(r"(?i)(?:\(laptop\)|laptop|\(Notebook\)|Notebook|\(m\))",  "Mobile", gpu)
    #             gpu = re.sub(r"(?i)(?:\sm\s|\sm$)",  " Mobile", gpu)
    #             gpu = re.sub(r"(?i)\s$",  "", gpu)
    #             gpu = re.sub(r"(?i)\s\s$",  "", gpu)
    #             gpu = re.sub(r"(?i)[)(]",  "", gpu)
    #             # Intel GPUs stonger than the weakest intel GPU available for user selection.
    #             find_strong_intel_gpus = re.findall(r'(?i)(?:(?:u?hd|iris)\s((?:630|620|530|520|540|550|6000|5600|xe|plus|pro)(?:\s|$)))', gpu)
    #             if find_strong_intel_gpus:
    #                 store_name = ""
    #             found_gpus += "" + store_name + ", "
    # return render_template(
    #     "result.html", user_gpu_name=user_gpu_name,
    #     user_game_id=user_game_id,
    #     user_game_name=user_game_name, steam=steam,
    #     found_gpus=found_gpus, info_message=info_message)

    # Find Regular Nvidia gpus from above 9000 series except for Titan and Quadro series.
    # Eg.'Geforce GT 740', 'Geforce RTX 2050 ti '
    # TESTING 
    # Tests Regex code that finds newer Nvidia Geforce GPUs.
    # with open('/workspace/milestone_3.1/static/data/gpu1.json', 'r') as json_file:
    #     gpu_list=json_file.read()
    # list = json.loads(gpu_list)
    # gpu_requirements = json.dumps(list)
    # with open("static/data/wiki.html") as wiki:
    #     soup = BeautifulSoup(wiki, "html.parser")
    #     find = str(soup)

    # test = ""
    # count = 0
    # count2 = 0
    # # gpu_requirements = "NVIDIA GeForce GTX 1060-5GB NVIDIA GeForce MX250 (25W)"
    # find_newer_gtx_gpu = re.findall(
    #     r'(?i)\s(?:geforce\s|gtx\s|gt\s|rtx\s|gts\s|g|mx|m|\d+[a-zA-Z]*)'
    #     r'(?:\d+\s*-*\d+gb|\d*[a-zA-Z]*\s*\d*\s*)'
    #     r'(?:max-q|NotebookR|max\sq|\(max\sq\)|\(max-q\)|max\sq|ti\sboost|ti|le'
    #     r'|super\smax-q|se|super|\d+m|\(laptop\)|laptop|\(mobile\)|mobile|\(m\)'
    #     r'|m|\(notebook\)|notebook|\(notebook\srefresh\)|\(\d+watts\)|\d+watts|\(\d+w\)|\d+w)*'
    #     r'(?:\smax-q|\smax\sq|\s\(max\sq\)|\s\(max-q\)|\s\(*mobile\)*|\s\(*m\)*|\s\(laptop\)'
    #     r'|\slaptop|\sNotebookR|\s\(notebook\srefresh\)|\snotebook\srefresh|\s\(notebook\)|\snotebook'
    #     r'|-\d+gb|\s\d+gb|\d+\sgb|\s\(refresh\)|\srefresh||\s\(\d+watts\)|\s\d+watts|\s\(\d+w\)|\s\d+w)*', gpu_requirements)
    # if find_newer_gtx_gpu:
    #     for gpu in find_newer_gtx_gpu:
    #         # Formats String to be compatible with database
    #         gpu = re.sub(r"GeForce",  "", gpu)
    #         gpu = re.sub(r"\s\s",  " ", gpu)
    #         gpu = re.sub(r"^\s",  "", gpu)
    #         gpu = re.sub(r"\s\s$",  "", gpu)
    #         gpu = re.sub(r"\s$",  "", gpu)
    #         gpu = re.sub(r"^",  "NVIDIA GeForce ", gpu)
    #         gpu = re.sub(r"(?:\(laptop\srefresh\)|laptop\srefresh|\(mobile\srefresh\)"
    #         r'|mobile\srefresh|\(m\srefresh\)|m\srefresh|\(notebook\srefresh\)|\snotebook\srefresh)',  "NotebookR", gpu)
    #         gpu = re.sub(r"(?:\(laptop\)$|laptop$|\(mobile\)$|mobile$|\(m\)$)",  "Notebook", gpu)
    #         gpu = re.sub(r"(?:\sm|\sm$)",  " Notebook", gpu)
    #         gpu = re.sub(r"[)(]",  "", gpu)
    #         gpu = re.sub(r"(?:watts|watts$)",  "w", gpu)
    #         gpu = re.sub(r"\s\s",  " ", gpu)
    #         check = mongo.db.strong_gpu.find({ "model": { "$regex": "^" + gpu + "$" , "$options": "i"} })
    #         for i in check:
    #             if str(i["model"]) == str(gpu):
    #                 test += "<p>" + i["model"] + "</p>" +"<p>" + i["rating"] + "</p>"
    #                 print(str(gpu))
    #                 print(str(i["model"]))
    #                 print("------------------")
    # return render_template("test.html", test=test)
            # if check:
            #     for i in check:
            #         print("----------------------------------------")
            #         print(gpu)
            #         print(i)
            #         if gpu != i["model"] :
            #             a = "x"
                        
            #         elif gpu == i["model"]:
            #             print("equals gpu")
            #             print(gpu)
            #             test += "<p>Mongo:" + i["model"] + "</p>" +"<p>JSON:" + gpu + "</p>"
            #             # Finds GPU rating 
            #             rating = int(i["rating"])
            #             # Compares the GPU rating against the user's GPU
            #             if user_gpu_rating <= rating:
            #                 info_message = message_success
            #             elif user_gpu_rating > rating:
            #                 info_message = message_fail
            #             else:
            #                 pass
            #         else:
            #             pass
    #     else:
    #         pass
    # return render_template("test.html", test=test)

    # find all Nvidia titan gpus in user gpu database
    # eg "NVIDIA Titan Xp Collector's Edition", 'NVIDIA Titan Xp'
    # 'NVIDIA Titan X (Pascal)', 'NVIDIA GTX TITAN X', 'NVIDIA GTX Titan Black'
    found_gpus = ""
    with open("static/data/wiki-nvidia.html") as wiki:
        soup = BeautifulSoup(wiki, "html.parser")
        gpu_requirements = str(soup)

    # find_nvidia_titan = re.findall(
    #     r'(?i)(?:geforce\sgtx\stitan|nvidia\sgtx\stitan|nvidia\stitan|titan)'
    #     r'\s(?:rtx|gtx|X\s'
    #     r'\(?Pascal\)?|Xp\sCollector\'s\sEdition|xp|x|V|5|black)',
    #     gpu_requirements)
    # if find_nvidia_titan:
    #     for gpu in find_nvidia_titan:
    #         print(gpu)
    #         # Formats String to be compatible with database
    #         store_name = gpu
    #         gpu = re.sub(r"^\s",  "", gpu)
    #         gpu = re.sub(r"\s\s$",  "", gpu)
    #         gpu = re.sub(r"\s$",  "", gpu)
    #         gpu = re.sub(r"  ",  " ", gpu)
    #         found_gpus += "" + store_name + ", "
    # return render_template(
    #     "result.html", user_gpu_name=user_gpu_name,
    #     user_game_id=user_game_id,
    #     user_game_name=user_game_name, steam=steam,
    #     found_gpus=found_gpus, info_message=info_message)


    find_nvidia_quadro = re.findall(
        r'(?i)(?:quadro\srtx|rtx|quadro\snvs|nvs|quadro[2-4]|quadro\sfx|quadro)\s'
        r'(?:plex\s\d{3,4}|k*m*g*v*p*a*t*\d{3,4}d*m*|cx|ddr|mxr|ex|pro|dcc|\d{3}xgl'
        r'|fx\s\d{3,4}g*x*2*(?:\ssdi|\slp|)|fx\s\d{3,4}|\d{2})*\s*(?:go\d{3,4}'
        r'|go\sgl|go|max-q)*', gpu_requirements)
    if find_nvidia_quadro:
        for gpu in find_nvidia_quadro:
            # Formats String to be compatible with database
            store_name = gpu
            gpu = re.sub(r"^\s",  "", gpu)
            gpu = re.sub(r"\s\s$",  "", gpu)
            gpu = re.sub(r"\s$",  "", gpu)
            gpu = re.sub(r"  ",  " ", gpu)
            found_gpus += "" + store_name + ", "
    return render_template(
        "result.html", user_gpu_name=user_gpu_name,
        user_game_id=user_game_id,
        user_game_name=user_game_name, steam=steam,
        found_gpus=found_gpus, info_message=info_message)



    #         check = mongo.db.gpu.find_one(
    #             {"$text": {"$search": "\"" + gpu + "\""}})
    #         if check:
    #             # Finds GPU rating
    #             rating = int(check['rating'])
    #             # Compares the GPU rating against the user's GPU
    #             if user_gpu_rating <= rating:
    #                 info_message = message_success
    #             elif user_gpu_rating > rating:
    #                 info_message = message_fail
    #             else:
    #                 pass
    #         else:
    #             pass
    # else:
    #     pass

    # # Find AMD RX graphics cards
    # find_new_amd_rx__gpu = re.findall(
    #     r"(?i)(?:radeon|ati|amd)\srx\s\d*[a-zA-Z]*\s*", gpu_requirements)
    # if find_new_amd_rx__gpu:
    #     for gpu in find_new_amd_rx__gpu:
    #         # Formats String to be compatible with database
    #         gpu = re.sub(r"(?i)ati",  "radeon", gpu)
    #         gpu = re.sub(r"(?i)amd",  "radeon", gpu)
    #         gpu = re.sub(r"^\s",  "", gpu)
    #         gpu = re.sub(r"\s\s$",  "", gpu)
    #         gpu = re.sub(r"\s$",  "", gpu)
    #         check = mongo.db.gpu.find_one(
    #             {"$text": {"$search": "\"" + gpu + "\""}})
    #         if check:
    #             rating = int(check['rating'])
    #             if user_gpu_rating <= rating:
    #                 info_message = message_success
    #             elif user_gpu_rating > rating:
    #                 info_message = message_fail
    #             else:
    #                 pass
    # else:
    #     pass

    # # Finds newer AMD GPUs
    # find_new_amd_gpu = re.findall(
    #     r'(?i)(?:mobility\sradeon|mobility|radeon|ati|amd)\s'
    #     r'(?:hd|r[579x]|VII)\s\d*[a-zA-Z]*\d*\s*'
    #     r'(?:xt|x2|boost|x|duo|56|64\sliquid|64)*', gpu_requirements)
    # if find_new_amd_gpu:
    #     for gpu in find_new_amd_gpu:
    #         # Formats String to be compatible with database
    #         gpu = re.sub(r"(?i)ati",  "", gpu)
    #         gpu = re.sub(r"(?i)amd",  "", gpu)
    #         gpu = re.sub(r"(?i)radeon",  "", gpu)
    #         gpu = re.sub(r"^",  "AMD Radeon ", gpu)
    #         gpu = re.sub(r"\s\s",  " ", gpu)
    #         gpu = re.sub(r"\s\s$",  "", gpu)
    #         gpu = re.sub(r"\s$",  "", gpu)
    #         # searches weaker GPU database
    #         check = mongo.db.weaker_gpu.find_one(
    #             {"$text": {"$search": "\"" + gpu + "\""}})
    #         if check:
    #             # If it finds one, this means the users GPU is
    #             # automatically better. User informed of success.
    #             info_message = message_success
    #         else:
    #             # Checks the database for GPUs that may or
    #             # may not be more powerful
    #             check = mongo.db.gpu.find_one(
    #                 {"$text": {"$search": "\"" + gpu + "\""}})
    #             if check:
    #                 # Finds GPU rating
    #                 rating = int(check['rating'])
    #                 # Compares the GPU rating against the user's GPU
    #                 if user_gpu_rating <= rating:
    #                     info_message = message_success
    #                 elif user_gpu_rating > rating:
    #                     info_message = message_fail
    #                 else:
    #                     pass
    # else:
    #     pass

    # # If GPU is found to be strong enough, the users inputed game is added to an array 
    # # that stores a list of compatible games within the GPU entity in the database.
    # if info_message == message_success:
    #     mongo.db.gpu.update_one(
    #         {"model": user_gpu_name},
    #         {"$push": {'games': {"name": user_game_name}}})
    #     print("Added to database")

    return render_template(
        "result.html", user_gpu_name=user_gpu_name,
        user_game_id=user_game_id,
        user_game_name=user_game_name, steam=steam,
        gpu_requirements=gpu_requirements, info_message=info_message)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
