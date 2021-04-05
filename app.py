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
    user_gpu_rating = int(request.form.get('gpu-rating'))
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
    # steam = "512mb vram + 32mb+ vram 128mb graphics card+ 256 mb video cardGraphics: Radeon RX 5300M Radeon 625 Radeon RX 560X radeon R9 M470 Radeon R9 M275X Radeon R9 M470X Radeon HD 8850M Radeon HD 7520G Radeon HD 7770M Mobility Radeon HD 5470 Mobility Radeon HD 550v Mobility Radeon HD 4250 Mobility Radeon HD 2400 XT Mobility Radeon X2300 Radeon RX 6800 Radeon RX 6900 X Radeon RX Vega 56 Radeon RX Vega 64 Liquid Radeon 520 Radeon 530 Radeon RX 550X Radeon RX 470D Radeon R9 380X Radeon R9 Fury X Radeon Pro Duo Radeon HD 8570 NVIDIA Titan Xp Collector's Edition NVIDIA Titan Xp NVIDIA Titan X (Pascal) NVIDIA GTX TITAN X NVIDIA GTX Titan Black NVIDIA Titan RTX NVIDIA Titan V Vram: 32mb Nvidia Gefore GTX 640 or NVIDIA GeForce GT 740 or NVIDIA GeForce GT 640m Radeon ve/7000 Radeon le7100 Radeonsdr Radeon ddr Radeon 7500 Radeon 340 Radeon 9250 Radeon 9100 Radeon 9800 Radeon xpress GeForce RTX 2050 ti (notebook) GeForce GTX 2090 ti notebook GeForce RTX 2080 ti boost GeForce RTX 2070 notebook GeForce RTX 2010 (notebook) GeForce RTX 2070 ti boost Super Max-Q GeForce GTS 160M GeForce GTS 250 GeForce GTX 560 SE GeForce MX110 GeForce M120 NVIDIA GeForce GTX 850M GeForce GT 520MX GeForce RTX 2070 Max-Q GeForce MX45 radeon 520 radeon 530 radeon 8500 Radeon Radeon amd x300 Radeon ati x1050 geforce gtx 5000 ti nvidia titan x nvidia gt 300 super Radeon x700 Radeon x800 xt Radeon hd 2350 Radeon hd 2900 Radeon hd 3400 Radeon 3100 Radeon hd 4300 Radeon hd 4250 Radeon hd 5400 Radeon hd 6750 Radeon hd 6600 Radeon hd 5500 4 MB Video Card NVIDIA 7800GT NVIDIA 7800GTx NVIDIA geforce 6666GTx intel uhd 620 NVIDIA 9990 GT 256MB graphics card or better,GeForce3 Ti200 GeForce 256 DDR GeForce2 MX GeForce4 Ti4200 8x GeForce FX 5800 Ultra GeForce 6800 GT GeForce 7800 GTX GeForce 7300 SE GeForce G 100 GeForce 8800 Ultra GeForce GT 120 GeForce 9400 mGPU GeForce GT 140 ATI Radeon X1900 256MB graphics card or better"
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
        info_message = message_not_found
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
        return render_template(
        "result.html",info_message=message_fail)

    '''
    Because all user GPUs are above 1GB VRAM,
    and only older GPU's VRAM is measured in MB, 512MB and below.
    If the first regex pattern below finds these, it returns a success message
    because the GPU is certain to be weaker than the users.
    '''
    # Find old gpus under 1GB
    old_gpu = re.findall(r"\d+MB|\d+\sMB", gpu_requirements)
    if old_gpu:
        info_message = message_success

    '''
    Below fixes naming inconsistancies found
    in the Steam API files for Nvidia GPUs
    '''
    # Fix Steam Nvidia naming inconsistencies to align with this app's database
    # Eg. Geforce 7800GTX > Geforce 7800 GTX or Nvidia 7800GT > Geforce 7800 GT
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
            a = re.sub(r"(?i)(?:GTX|GT)", lambda ele: " " + ele[0] + " ", i)
            switch = a
            gpu_requirements = re.sub(before,  switch, gpu_requirements)
    else:
        pass

    '''
    The below regex patterns find AMD and Nvidia GPUs that are below the power
    of the weakest GPU the user can choose. If any of these patterns are
    matched, the user info message will be success.
    '''

    # Find old geforce gpus. Geforce 256, geforce2 - geforce4, geforce fx
    # geforce 6000, geforce 7000, geforce 8000, geforce 9000 series.
    find_old_geforce_gpu = re.findall(
        r'(?i)(?:nvidia\sgeforce|NVIDIA|geforce\d*)\s'
        r'(?:(?:ti|mx|pcx)\d+|fx|pcx|\d+|\d+\s\+|\d+a|\d+pv)\s*'
        r'(?:\d+gtx\+'
        r'|gtx|gso|gt|gx2|ge|gs|le|se|mgpu|ultra|TurboCache|nForce\s4[1-3]0)'
        r'*\s(?:ultra)*', gpu_requirements)
    if find_old_geforce_gpu:
        info_message = message_success
    else:
        pass

    # Finds AMD GPU years 2001-2008 or from Radeon 8000 series - HD 3000 series
    # Eg. Radeon X700, Radeon X1300 XT, Radeon X1900 GT, Radeon HD 2900 PRO
    find_old_amd_gpu = re.findall(
        r'(?i)(?:radeon|ati|amd)\s'
        r'(?:hd|x\d+|xpress\s\d+|xpress|8\d+|9\d+)\s'
        r'(?:[2-3]\d+\s(?:pro|xt|gt|x2|\d+)*'
        r'|[1-2]\d+|x\d+|le|pro|se|xt|xxl|xl|agp|gto|gt|x)', gpu_requirements)
    if find_old_amd_gpu:
        info_message = message_success
    else:
        pass

    # Finds more old varients of AMD GPUs. Aids the above pattern to find more.
    find_x_amd_gpu = re.findall(
        r'(?i)(?:radeon|ati|amd)\sx\d+\s'
        r'(?:le|pro|se|xt|xxl|xl|agp|gto|gt|x)"', gpu_requirements)
    if find_x_amd_gpu:
        info_message = message_success
    else:
        pass

    # Find mobile Amd gpu that are less powerful than all gpus on user gpu list
    find_old_amd_mobile_gpu = re.findall(
        r'(?i)(?:mobility\sradeon|mobility)\s(?:hd|x)*\s*'
        r'(?:[1-3][0-9]\d+|4[0-5]\d+)\s*(?:x2|xt)*', gpu_requirements)
    if find_old_amd_mobile_gpu:
        info_message = message_success
    else:
        pass

    '''
    The below code will find any patterns that are for GPUs not guaranteed
    to be less powerful than the user GPU.
    They will find the patterns in the Steam API json and search
    MongoDB to find a match.
    If it finds a match, it will compare the GPU rating field of both the users
    GPU and the GPU on in the API json.
    If the user gpu is a higher rating, they receive a success message.
    '''
    # Find intel integrated graphics cards
    # eg. intel hd 3000 and Intel hd 620
    find_intel_gpu = re.findall(r'(?i)intel\su?hd\s\d+[a-zA-Z]{0,2}',
                                gpu_requirements)
    if find_intel_gpu:
        for gpu in find_intel_gpu:
            # Formats out any unwanted whitespace
            gpu = re.sub(r"^\s",  "", gpu)
            gpu = re.sub(r"\s\s$",  "", gpu)
            gpu = re.sub(r"\s$",  "", gpu)
            gpu = re.sub(r"  ",  " ", gpu)
            # searches weaker GPU database
            check = mongo.db.weaker_gpu.find_one(
                {"$text": {"$search": "\"" + gpu + "\""}})
            if check:
                # If it finds one, this means the users GPU is
                # automatically better. User informed of success.
                info_message = message_success
            else:
                # Checks the database for GPUs that may or
                # may not be more powerful
                check = mongo.db.gpu.find_one(
                    {"$text": {"$search": "\"" + gpu + "\""}})
                if check:
                    # Finds GPU rating
                    rating = int(check['rating'])
                    # Compares the GPU rating against the user's GPU
                    if user_gpu_rating <= rating:
                        info_message = message_success
                    elif user_gpu_rating >= rating:
                        info_message = message_fail
                    else:
                        pass
    else:
        pass

    # Find Regular Nvidia gpus from above 9000 series exept for titan series
    # Eg.'Geforce GT 740', 'Geforce RTX 2050 ti (notebook)',
    find_newer_gtx_gpu = re.findall(
        r'(?i)\s(?:gtx\s|gt\s|rtx\s|gts\s|mx|m)\d*[a-zA-Z]*\s*\d*\s*'
        r'(?:GB|ti\sboost|ti\s\(?notebook\)*|ti|le|max-q|super\smax-q'
        r'|se|super|\d+m|\(?mobile\)*|\(?notebook\)?)*', gpu_requirements)
    if find_newer_gtx_gpu:
        for gpu in find_newer_gtx_gpu:
            # Formats String to be compatible with database
            gpu = re.sub(r"(?i)\d+GB",  "", gpu)
            gpu = re.sub(r"^",  "NVIDIA GeForce", gpu)
            gpu = re.sub(r"\s\s$",  "", gpu)
            gpu = re.sub(r"\s$",  "", gpu)
            # searches weaker GPU database
            check = mongo.db.weaker_gpu.find_one(
                {"$text": {"$search": "\"" + gpu + "\""}})
            if check:
                # If it finds one, this means the users GPU is
                # automatically better. User informed of success.
                info_message = message_success
            else:
                # Checks the database for GPUs that may or
                # may not be more powerful
                check = mongo.db.gpu.find_one(
                    {"$text": {"$search": "\"" + gpu + "\""}})
                if check:
                    # Finds GPU rating
                    rating = int(check['rating'])
                    # Compares the GPU rating against the user's GPU
                    if user_gpu_rating <= rating:
                        info_message = message_success
                    elif user_gpu_rating >= rating:
                        info_message = message_fail
                    else:
                        pass
    else:
        pass

    # find all Nvidia titan gpus in user gpu database
    # eg "NVIDIA Titan Xp Collector's Edition", 'NVIDIA Titan Xp'
    # 'NVIDIA Titan X (Pascal)', 'NVIDIA GTX TITAN X', 'NVIDIA GTX Titan Black'
    find_nvidia_titan = re.findall(
        r'(?i)\s(?:geforce\sgtx\stitan|nvidia\sgtx\stitan|nvidia\stitan|titan)'
        r'\s(?:rtx|gtx|X\s'
        r'\(?Pascal\)?|Xp\sCollector\'s\sEdition|xp|x|V|5|black)',
        gpu_requirements)
    if find_newer_gtx_gpu:
        for gpu in find_nvidia_titan:
            # Formats String to be compatible with database
            gpu = re.sub(r"Geforce",  "", gpu)
            gpu = re.sub(r"^\s",  "", gpu)
            gpu = re.sub(r"\s\s$",  "", gpu)
            gpu = re.sub(r"\s$",  "", gpu)
            gpu = re.sub(r"  ",  " ", gpu)
            check = mongo.db.gpu.find_one(
                {"$text": {"$search": "\"" + gpu + "\""}})
            if check:
                # Finds GPU rating
                rating = int(check['rating'])
                # Compares the GPU rating against the user's GPU
                if user_gpu_rating <= rating:
                    info_message = message_success
                elif user_gpu_rating >= rating:
                    info_message = message_fail
                else:
                    pass
            else:
                pass
    else:
        pass

    # Find AMD RX graphics cards
    find_new_amd_rx__gpu = re.findall(
        r"(?i)(?:radeon|ati|amd)\srx\s\d*[a-zA-Z]*\s*", gpu_requirements)
    if find_new_amd_rx__gpu:
        for gpu in find_new_amd_rx__gpu:
            # Formats String to be compatible with database
            gpu = re.sub(r"(?i)ati",  "radeon", gpu)
            gpu = re.sub(r"(?i)amd",  "radeon", gpu)
            gpu = re.sub(r"^\s",  "", gpu)
            gpu = re.sub(r"\s\s$",  "", gpu)
            gpu = re.sub(r"\s$",  "", gpu)
            check = mongo.db.gpu.find_one(
                {"$text": {"$search": "\"" + gpu + "\""}})
            if check:
                rating = int(check['rating'])
                if user_gpu_rating <= rating:
                    info_message = message_success
                elif user_gpu_rating >= rating:
                    info_message = message_fail
                else:
                    pass
    else:
        pass

    # Finds newer AMD GPUs
    find_new_amd_gpu = re.findall(
        r'(?i)(?:mobility\sradeon|mobility|radeon|ati|amd)\s'
        r'(?:hd|r[579x]|VII)\s\d*[a-zA-Z]*\d*\s*'
        r'(?:xt|x2|boost|x|duo|56|64\sliquid|64)*', gpu_requirements)
    if find_new_amd_gpu:
        for gpu in find_new_amd_gpu:
            # Formats String to be compatible with database
            gpu = re.sub(r"(?i)ati",  "", gpu)
            gpu = re.sub(r"(?i)amd",  "", gpu)
            gpu = re.sub(r"(?i)radeon",  "", gpu)
            gpu = re.sub(r"^",  "AMD Radeon ", gpu)
            gpu = re.sub(r"\s\s",  " ", gpu)
            gpu = re.sub(r"\s\s$",  "", gpu)
            gpu = re.sub(r"\s$",  "", gpu)
            # searches weaker GPU database
            check = mongo.db.weaker_gpu.find_one(
                {"$text": {"$search": "\"" + gpu + "\""}})
            if check:
                # If it finds one, this means the users GPU is
                # automatically better. User informed of success.
                info_message = message_success
            else:
                # Checks the database for GPUs that may or
                # may not be more powerful
                check = mongo.db.gpu.find_one(
                    {"$text": {"$search": "\"" + gpu + "\""}})
                if check:
                    # Finds GPU rating
                    rating = int(check['rating'])
                    # Compares the GPU rating against the user's GPU
                    if user_gpu_rating <= rating:
                        info_message = message_success
                    elif user_gpu_rating >= rating:
                        info_message = message_fail
                    else:
                        pass
    else:
        pass

    if info_message == message_success:
        mongo.db.gpu.update_one({ "model": user_gpu_name },{ "$push": { 'games': { "name": user_game_name}}})


    return render_template(
        "result.html", user_gpu_name=user_gpu_name,
        user_game_id=user_game_id,
        user_game_name=user_game_name, steam=steam,
        gpu_requirements=gpu_requirements, info_message=info_message)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
