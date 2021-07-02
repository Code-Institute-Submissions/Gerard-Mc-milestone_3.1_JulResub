# [GPUForce](http://milestone-3-gerard.herokuapp.com/)

GPUForce is a website that gamers can go to when they want to know if their gpu is powerful enough to play a game before they buy it. It will let them know by comparing their GPU to the minimum requirements posted on the games Steam store page. To get more info, they can register and see the average frames-per-second(FPS), a key metric of performance and playability, that other users were able to achieve on the same GPU as them. They will also have the ability to see a full list of games that have been found to run on their GPU model up to that point in time. And if they're feeling generous, they can enter what FPS they were able to achieve too.

## UX

### User Stories

#### As a general or 1st-time user, I would like to...

* check if my GPU is powerful enough to play a particular game.
* view what the GPU requirements the game developers recommended to play the game.
* view the website on mobile, tablet, and desktop/laptop size screens.

#### As a regular user, I would like to...

* create my own account.
* login to my account.
* logout of my account.
* delete my account.
* input the FPS I achieved.
* edit the FPS I achieved.
* input my GPU model to my profile.
* edit my GPU model in my profile.
* view the average FPS users with my GPU were able to achieve with a game I'm interested in.
* view a list of games compatible with my GPU.

#### As the site owner, I would like to...

* use all features available to general users for testing purposes.
* have the abilty to quickly add new GPUs and their performance rating to a database.
* have the ability to delete a gpu from the database.
* have all GPUs rating automatically change accordingly when there has been a removal or insertion of a GPU to the database. 

### Design

The general design is one of a dark techy fluorescent look that users of these sites would come to expect because that's usually how they are presented.

This was to make it seem familiar and of that gamer scene.

#### Color

The background image of a gaming laptop was chosen because it's relevant but also because of its deep purple and fluorescent lighting effect. 

A radioactive green was used as it complimented the purple but also work in a UX capacity because it stands out, and therefore good for guiding the user through 

the steps needed to complete tasks like searching for games and GPUs. This is is hex color code: #bebebe.

A complimentary orange-ish color was picked using the Adobe Color website. This was used to visually caution the site owner of the delete button. The hex code: #FA4119.

#### Typography

A font named Orbitron was used for much of the site as it suited the tech style aimed for. For parts where reading needs to be easier, a font named Roboto was used 

because it's informal enough to suit the site and is very easy to read.


### Wireframes

The wireframes are just simple sketches of what the layout was to become.

They can be found in the link below.

[Wireframes](readme_files/wireframes)


## Features


### Existing Features

#### Home Page Search Engine

On the home page, there is a section with a form to search for games, a form to search for GPUs, and a submit form with a hidden text area that sends the GPU and 

game search data to the back end where it performs queries and comparison logic.

##### The Game Search Form

* The game search form takes input from the user and sends the data to flask. In flask, the data is used in a MongoDB query that searches a game collection of 100,000 games provided by the games store Steam's API, which sends back all the closest matches. This contains the game name and ID. (This ID is used for retrieving a larger JSON file with PC requirements from the steam API after the main form  with the hidden text is submitted) 
* The user then selects the game if it comes back. This is stored in the hidden textarea in the form below.

##### The GPU Search Form

* Much like above, the user inputs and submits data in the GPU search form which is sent to flask, embedded in a query that searches a collection of the 200 most powerful modern desktop/laptop GPUs.
* The user selects the best match and the data is stored in the hidden text area.

##### The Main Submit Form
* When the user has chosen a game and GPU, they can hit submit. The data is sent to a view in Flask. The game id is embedded in a request to the Steam API and retrieves a JSON file with the full game information.
* Regex is used to find compatible GPUs in the minimum requirements section of the JSON file. 
* There are three regex pattern-finding procedures.
* First the regex is programmed to find all NVIDIA, AMD, and Intel GPUs that are weaker than the 200 GPUs the user can choose from.
* If it matches one of these GPUs, the program ends and the user is informed that the GPU is compatible.
* Second, If the old less powerful GPUs are not found by the regex, the view runs regex that finds all new variants of these GPUs. But they could be on the list of 200 top GPUs that the user can select from, and therwfore need to be compared with the user's GPU.
* So patterns matched in the Steam JSON file that are of new varients are put into a query sent to the 200 GPU collection in mongo.
* If found, the rating is compared to the user's GPU rating, and if it has a worse rating, the program ends and the user is informed that they can play the game.
* Third, and for good measure, if the above finds nothing in the MongoDB collection, the patterns found of the newer GPU variants are sent in a query to a collection of a few hundred more GPUs that are weaker than the 200 GPUS.
* If found, the user is told they can play the game. If not, everything that we can try has been attempted and the user is informed that we don't have this GPU/game combo on the database.

The last search may seem superfluous, but it is necessary because the 1st run(checking for the GPU patterns that are guaranteed to be weaker), only matches GPUs from up to around 2008 because, after that, most are weaker but a lot stronger than the weaker of the 200 the user can choose from.

As the site owner starts to increase the list of the 200 ranked GPUs, the 1st and 3rd steps in searching the weak GPU database and the pre-2009 GPU patterns won't be necessary. But while the list is only at 200, they are needed to make the search engine provide results to the user.

Capability to grow the list has been built into the admin page.


* If any of the three sequences of code is successful, the game is added to an array in the GPU entity in MongoDB to build an array of games that are compatible with this GPU. (This allows for a list to be given to a registered user containing a list of games compatible with their GPU on their profile page).

#### The Profile Page

* The user can select a GPU to be added to their user entity. This can be changed.
* A list of games compatible with this GPU that was populated by all prior successful game/GPU searches done by all users is displayed under it.
* The user can enter the FPS they achieved with any games that display along with viewing the average FPS entered by other users for this game/GPU combo.
* The user can update the FPS as much as they like.

#### The Admin Page

* A list of the 200 GPUs and their rating is displayed.
* If the user has a GPU to enter and knows its rating compared to one in the list. They can replace that GPU with the new one.
The new one will take the rating of the GPU it replaced.
* The GPU and all GPUs under will have their rating decreased by one by the backend.
* A GPU can be deleted.
* When a GPU is deleted, all GPUs under it have their rating increased by one, with the one below it taking it's place.

#### Login and Register

* The user can log in and register for access to the extra features like viewing average FPS, inputting FPS, and seeing a list of all games found to be compatible with their GPU.

### Missing features to be implemented

* Ability for the user to delete their account.
* Ability for the user to update thier password and username.
* Automatically add the user's GPU into the search box on the Home page when logged in for better UX.
* Add game JSON files to a database when regex fails to find anything. Could be used for analysis to improve the regex. These could be accessed on the admin page.
* Autocomplete inputs on the home page for better UX.
* Larger list of GPUs.

## Technologies Used

* [HTML](https://developer.mozilla.org/en-US/docs/Web/HTML) Markup language used for building all webpages on the site.
* [CSS3](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS3)  Declarative language used to style the project.
* [Gitpod](https://www.gitpod.io/) Gitpod is an IDE. All coding was done using Gitpod.
* [GitHub](https://github.com/)  Github a Git repository hosting service. Was used to store all versions of this project as it progressed.
* [Heroku](https://www.heroku.com)  Cloud platform used to host the project.
* [Regex](https://en.wikipedia.org/wiki/Regular_expression) A regular language. Used throughout the project for pattern finding.
* [Bootstrap 4.5](https://https://getbootstrap.com/) Use for a lot of the styling and layout.
* [jQuery 3.5](//https://jquery.com/) Used by Bootstrap to do what Bootstrap does for the most part.
* [Flask 1.1.2](https://palletsprojects.com/p/flask/) Very useful framework used for creating the backend of the site.
* [Python 3.8.8 ](https://www.python.org/) Used form back-end programming.
* [Jinja 2.11.3](https://pypi.org/project/Jinja2/) Templating language used with Flask.
* [MongoDB Atlas](https://www.mongodb.com/) Cloud database used to store the projects database.
* [PyMongo 3.11.3](https://pypi.org/project/pymongo/) An API used by Python to communicate with MongoDB. 


## Testing

### Register
10 accounts were registered including an admin account. After registration, the page was directed to a profile page for the new user and a flash message displayed as expected. After this, all users were found in the appropriate collection with an id an password in the MongoDB Atlas database.

### Login 

The accounts were tested by logging out and login in again, and after entering the username and password, the page was redirected to a profile page for the user as expected. A print(session["user"]) statement was added after the password and username check and just before the redirect url in the login view. The user session data would be expected to be the same as the login username and it was.

### Profile Page

- #### Access Without Being Logged in as User
To make sure the profile page isn't accessible without being logged in, the profile page URL was copied and then the user was logged out. When the URL was pasted into the browser's address bar and enter was hit, the page was redirected to the login page with the expected flash message. 
When the same was tried with the admin profile page, it too was redirected to the login page with its expected flash message.

- #### Choose a GPU
A GPU was chosen for the users and it was displayed on the screen and also added to the user entity in the MongoDB Atlas user collection.
After this, the GPU was edited and a new one was selected. It displayed on the screen and the user entity now had the GPU in its GPU field.

- #### Display Average FPS, User FPS, and Edit user FPS

After the GPU was selected, the list of games stored in the array in the GPU entity from the GPU collection in Mongo was displayed, along with the average value from all the user FPS data that is stored in objects within an array of games associated with the user's chosen GPU. The individual values were counted and the average calculated and it matched what was on the screen. It was done manually by putting in a value into a game with no user fps, and then with a different user, and then taking the average of the values put in by each one. This came out as expected too.


When the user fps was edited on the profile page, the page updated and the new FPS value was displayed. It was found to be the same in Mongo too.

### Admin 

- #### Insert and Delete
After hitting the insert button, the input displayed as the JS is coded to do, and when the insert or close button was pressed it disappeared as expected. When the text was entered into the insert text field and submitted, the page refreshed and the new test was there with a rating of the GPU it replaced. The GPU it replaced and all others of a lower value had the rating decreased by one. This was repeated several times and each time it displayed as expected with MongoDb collection updating too.
The same tests were done for the delete functionality with the same result, only the GPUs under its rating increased by one.

### Home Search

Many game names and partial were typed in the game search form and games with appropriate names were returned. When a game was chosen from this list the hidden text area values changed as expected. This was seen in the developer panel in Chrome.
The same process was done for the GPU search form.

When the main submit button was pressed the results came back as expected. Modern games eg. CyberPunk, which needs strong GPUs were giving negative results for the weaker GPUs in the user GPU database and positive for the stronger ones. This was tried multiple times for strong and weak games, and the weak GPUs only ad success on less taxing games, and the strongest could play anything.

the use of print statements was used to track the values of the submitted user forms and data that came back for comparison in MongoDB. The statements were as expected every time.

The user FPS should only display when a user is logged in, otherwise, the user should see a message asking them to login or register to see the avg FPS for this game. 

This was tested by log in and out and comparing the results, and it worked as expected.

### Use of the Website at different Screen Sizes and Browsers

The site was designed to display correctly for screen sizes as low as 320px high and wide.
This was tested using Chrome tools. The search engine on the home page displays well down to these sizes. But once it gets below 310px of height, the user might not know that the search results have come back because they will be below the visual part of the screen. Very few people use phones of this size so it was decided not to tailor the design to sizes below 320px high or 300px wide.


### Known Bugs

When the user is updating or adding a GPU on their profile page, there are few steps to it.
* 1st, they press edit and the form is displayed.

* 2nd, the type in a GPU and press search

* 3rd, they choose a GPU and the profile page is reset with the updated GPU.

If they press back on the nav after the final step, they will see the previous GPU displayed as their GPU.

## Validation

[Validation](readme_files/validation)

All CSS, Python, Javascrip, and HTML was validated.

The only errors coming back are because the validators don't recognise Jinja, and the some ids are duplicated because they wouldn't be displayed when Jinja has control.


### Database Models

#### game

_id: <ObjectId>
app_id: <Int32>
name: <string>

#### strong_gpu

_id: <ObjectId>
model: <string>
rating: <Int32>
games: <Array>


#### users

_id: <ObjectId>
name: <string>
password: <string>
gpu: <string>

#### weaker_gpu
_id: <ObjectId>
model: <string>








