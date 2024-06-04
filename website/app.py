from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = 'secret_temp_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False) # This should be hashed in a real application I'll add bcrypt later
    details = db.relationship('UserDetails', backref='user', uselist=False)

class UserDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.String)
    degree_type = db.Column(db.String)
    school = db.Column(db.String)
    expected_graduation = db.Column(db.String)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template("index.html", user=user)
    else:
        message = request.args.get("message")
        return render_template("login.html", message=message)
    
@app.route("/signup", methods=["GET", "POST"])
def signup():
    print("Signup route reached!")
    if request.method == "GET":
        print("GET request received")
        message = request.args.get("message")
        return render_template("signup.html", message=message)
    elif request.method == "POST":
        print("POST request received")
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        new_user = User(first_name=first_name, last_name=last_name, email=email, password=password)
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login", message="Successfully Signed Up!"))
        except IntegrityError:
            db.session.rollback()
            return redirect(url_for("signup", message="Email address already registered!"))

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user:
            if user.password == password:
                session['user_id'] = user.id
                return redirect(url_for("index", message="Successfully logged in"))
            else:
                return redirect(url_for("index", message="Incorrect password"))
        else:
            return redirect(url_for("index", message="User with email '{}' does not exist".format(email)))
    else:
        message = request.args.get("message")
        return render_template("login.html", message=message)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = session.get('user_id')  # Check if 'user_id' exists in the session
    if user_id:
        user = User.query.get(user_id)
        if request.method == "GET":
            return render_template("profile.html", user=user)
        elif request.method == "POST":
            # Check if user details exist, if not, create them
            if user.details is None:
                user.details = UserDetails()
            user.details.location = request.form.get("location")
            user.details.degree_type = request.form.get("degree_type")
            user.details.school = request.form.get("school")
            user.details.expected_graduation = request.form.get("expected_graduation")
            db.session.commit()
            return redirect(url_for("profile"))
    else:
        return redirect(url_for("login")) # Redirect to login page if user_id is not in the session

@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove 'user_id' from session
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
