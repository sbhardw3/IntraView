from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = os.urandom(24)  # Generate a new secret key
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Company(db.Model):
    __tablename__ = 'company'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    location = db.Column(db.String, nullable=False)
    website = db.Column(db.String, nullable=False)
    review_count = db.Column(db.Integer, default=0)
    average_rating = db.Column(db.Float, default=0.0)

    def update_average_rating(self):
        reviews = Review.query.filter_by(company_id=self.id).all()
        total_ratings = sum(review.rating for review in reviews)
        self.average_rating = total_ratings / max(len(reviews), 1)
        self.review_count = len(reviews)

        db.session.commit()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    details = db.relationship('UserDetails', backref='user', uselist=False)
    reviews = db.relationship('Review', backref='user', lazy=True)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)  # Rating from 1 to 5 stars
    description = db.Column(db.Text)  # Optional text description
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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
        print("Getting companies")
        companies = Company.query.all()
        print("Got companies", companies)
        user = User.query.get(session['user_id'])
        return render_template("index.html", user=user, companies=companies)
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

@app.route('/create_listing', methods=['GET', 'POST'])
def create_listing():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    if request.method == 'POST':
        company_name = request.form['company_name']
        location = request.form['location']
        website = request.form['website']
        
        # Create a new Company instance and add it to the database
        new_company = Company(name=company_name, location=location, website=website)
        db.session.add(new_company)
        db.session.commit()
        
        return redirect(url_for('company_page', company_id=new_company.id))
    else:
        return render_template('create_listing.html')

@app.route('/company/<int:company_id>', methods=['GET', 'POST'])
def company_page(company_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    company = Company.query.get_or_404(company_id)
    reviews = Review.query.filter_by(company_id=company_id).all()

    if request.method == 'POST':
        user_id = session.get('user_id')  # Load user ID from session
        if user_id:
            rating = int(request.form['rating'])
            review_text = request.form['review_text']

            new_review = Review(
                company_id=company_id,
                user_id=user_id,  # Associate the review with the user
                rating=rating,
                description=review_text
            )

            db.session.add(new_review)
            db.session.commit()

            company.update_average_rating()

            # Pass the average rating to the template
            average_rating = company.average_rating

            return redirect(url_for('company_page', company_id=company_id, average_rating=average_rating))

    # Pass the average rating to the template
    average_rating = company.average_rating

    return render_template('company_page.html', company=company, reviews=reviews, average_rating=average_rating)


if __name__ == '__main__':
    app.run(debug=True)
