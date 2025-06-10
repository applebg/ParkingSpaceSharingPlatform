# app.py
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, RadioField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError, DataRequired
from flask_migrate import Migrate
from parking_lot import Parking_lot
from datetime import datetime
import importlib
import pandas as pd

# Initialize settings
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

#migrate db
migrate = Migrate(app, db)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model): #多重繼承
    '''Model for user authentication'''
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # either 'owner' or 'borrower'

# ParkingLotRegistration Model
class ParkingLotRegistration(db.Model):
    '''Model for parking lot registration'''
    __tablename__ = "parking_lots"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owned_parking_lot = db.Column(db.String(150), nullable=False)
    empty = db.Column(db.Boolean, default=True)
    booked = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='registrations')
    time_intervals = db.relationship('TimeInterval', backref='parking_lots', lazy=True)

# time interval model used by ParkingLotRegistration
class TimeInterval(db.Model):
    __tablename__ = "timeintervals"
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    # Foreign key linking each time interval to a parking lot registration
    parking_lot_id = db.Column(db.Integer, db.ForeignKey('parking_lots.id'), nullable=False)
class Borrower(db.Model):
    __tablename__ = 'borrowers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    # Foreign key linking to User model
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationship to access user details from Borrower
    user = db.relationship('User', backref=db.backref('borrowers', lazy=True))

    # Optional: Link to a specific parking lot if needed
    # parking_lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot_registration.id'))
    # parking_lot = db.relationship('ParkingLotRegistration', backref='borrowers')
    
    def __repr__(self):
        return f'<Borrower {self.name}, Parking from {self.start_time} to {self.end_time}>'


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Registration Form
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=4, max=150)])
    confirm_password = PasswordField('Confirm Password', validators=[InputRequired(), EqualTo('password')])
    role = RadioField('Role', choices=[('owner', 'Owner'), ('borrower', 'Borrower'), ('admin', 'Admin')], validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

# Login Form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=150)])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')


# Initialize the ParkingLot class (this manages all the parking spot logic)
parking_lot = Parking_lot()
parking_lot.input_txt("parking_lot_in.txt")

# define functions that deal with linking registration and parking lot management here
def link_reg_parking_lot():
    '''link registration data and parking lot area together'''
    # initialize the link between registration data and parking lot
    # get area first
    area = parking_lot.area
    # fetch data from db, and organize them into dictionary
    registration = ParkingLotRegistration.query.all()
    dic = {
        "owned_parking_lot": [],
        "status code": []
    }
    for record in registration:
        dic['owned_parking_lot'].append(record.owned_parking_lot)
        if record.empty == True and record.booked == False:
            dic['status code'].append(1)
        elif record.empty == False and record.booked == False:
            dic['status code'].append(2)
        elif record.empty == True and record.booked == True:
            dic['status code'].append(3)
        elif record.empty == False and record.booked == True:
            dic['status code'].append(4)
    # modify area
    for i in range(0, len(dic['owned_parking_lot'])):
        s = dic['owned_parking_lot'][i].split(",")
        x = s[0][1:]
        y = s[1][:-1]
        x = int(x)
        y = int(y)
        status = dic['status code'][i]
        area[x][y] = status

    parking_lot.output_txt(filename="parking_lot_in.txt")
    print('link registration to parking lots successful!')
def set_back_to_empty_unbooked(coordinate: str):
    '''after deleting a record, set the parking lot's status code to 1. Coordinate should look like this: (x,y) where x and y are integer'''
    # get area first
    area = parking_lot.area
    li = coordinate.split(",")
    x = li[0][1:] # select the number part of str
    x = int(x)
    y = li[1][:-1] # select the number part of str
    y = int(y)
    area[x][y] = 1
def all_set_back_to_empty_unbooked():
    '''this function will set status code 1,2,3,4 back to 1'''
    area = parking_lot.area
    for i in range(area.shape[0]):
        for j in range(area.shape[1]):
            if area[i,j] in [1,2,3,4]:
                area[i,j] = 1
    print(area)


# User authentication routes
@app.route('/')
@login_required
def home():
    return render_template('base.html', current_user_role = current_user.role)

@app.route('/home')
@login_required
def home2():
    return render_template('base.html', current_user_role = current_user.role)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, password=hashed_password, role = form.role.data)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! You can now log in.')
        return redirect(url_for('login'))
    elif form.is_submitted(): # this block implies that input is not successful
        flash("invalid input of data")
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password.')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile_auth.html')
# end of user authentication

# Routes that query the parking lot
@app.route('/query_empty_unbooked_lots', methods=['GET'])
def get_empty_unbooked_lots():
    lots = parking_lot.report_coordinate(1)
    return render_template("query_empty_unbooked_lots.html", lots=lots)

@app.route('/query_parked_lots', methods=['GET'])
def get_parked_lots():
    lots = parking_lot.report_coordinate(2)
    return render_template("query_parked_lots.html", lots=lots)

@app.route('/query_empty_booked_lots', methods=['GET'])
def get_empty_booked_lots():
    lots = parking_lot.report_coordinate(3)
    return render_template("query_empty_booked_lots.html", lots=lots)

@app.route('/query_parked_booked_lots', methods=['GET'])
def get_parked_booked_lots():
    lots = parking_lot.report_coordinate(4)
    return render_template("query_parked_booked_lots.html", lots=lots)
# end of query routes

# CRUD routes for registration
# this route allows owners to register his own parking lots but not timeintervals
@app.route('/registration/new', methods=['GET', 'POST'])
@login_required
def create_registration():
    # If the user is not an owner, do not allow him/her to proceed.
    if current_user.role != "owner":
        return "non owners are not allowed to add new records!"
    
    # get parking lot status code == 1
    available_lots = parking_lot.report_coordinate(1)
    # get currently registered parking lots
    registrations = db.session.query(ParkingLotRegistration).all()
    # remove registered lots from lots whose status code == 1 to get available lots
    for reg in registrations:
        try:
            available_lots.remove(reg.owned_parking_lot)
        except:
            print(f"no parking lot {reg.owned_parking_lot}")
        

    # note that some fields are disable temporarily 2025-01-08
    if request.method == 'POST':
        name = request.form['name']
        owned_parking_lot = request.form['owned_parking_lot']
        # start_time_str = request.form['start_time']
        # end_time_str = request.form['end_time']
        # empty = request.form.get('empty', False) == 'on'
        # booked = request.form.get('booked', False) == 'on'

        # Convert strings to datetime objects
        # start_time = datetime.fromisoformat(start_time_str)
        # end_time = datetime.fromisoformat(end_time_str)

        # Create and add the new ParkingLotRegistration
        new_registration = ParkingLotRegistration(
            name=name, 
            owned_parking_lot=owned_parking_lot, 
            # empty=empty, 
            # booked=booked,
            user_id=current_user.id)
        db.session.add(new_registration)
        db.session.commit()

        # Handle start_time and end_time for the new TimeInterval
        time_interval = TimeInterval(
            start_time=datetime(year=1900, month=1, day=1), # for now, star_time and end_time need not be specified. The value is dummy
            end_time=datetime(year=1900, month=1, day=1),
            parking_lot_id=new_registration.id  # Link TimeInterval to ParkingLotRegistration
        )

        db.session.add(time_interval)
        db.session.commit()

        link_reg_parking_lot()
        flash('New parking lot registration added successfully!')
        return redirect(url_for('get_registration'))

    return render_template('create_registration.html', username = current_user.username, parking_lot_list = available_lots) # Only the user.username is allowed to be added to parking_lots.name

@app.route('/registration/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def update_registration(id):
    registration = ParkingLotRegistration.query.get_or_404(id)
    timeinterval = TimeInterval.query.get_or_404(id)
    if request.method == 'POST':
        registration.name = request.form['name']
        registration.owned_parking_lot = request.form['owned_parking_lot']
        registration.empty = request.form.get('empty', False) == 'on'
        registration.booked = request.form.get('booked', False) == 'on'
    

        # handle start time / end time here
        start_time_str = request.form["start_time"]
        end_time_str = request.form["end_time"]
        # Convert strings to datetime objects
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        timeinterval.start_time = start_time
        timeinterval.end_time = end_time
        
        db.session.commit()
        all_set_back_to_empty_unbooked()
        link_reg_parking_lot()
        flash('Registration updated successfully!')
        return redirect(url_for('get_registration'))

    return render_template('edit_registration.html', registration=registration)

@app.route('/registration/delete/<int:id>', methods=['POST'])
@login_required
def delete_registration(id):
    registration = ParkingLotRegistration.query.get_or_404(id)
    timeinterval = TimeInterval.query.get_or_404(id)
    parking_lot_to_set_to_1 = registration.owned_parking_lot # this is str
    db.session.delete(timeinterval)
    db.session.delete(registration)
    db.session.commit()
    set_back_to_empty_unbooked(parking_lot_to_set_to_1)
    link_reg_parking_lot()
    flash('Registration deleted successfully!')
    return redirect(url_for('get_registration'))
# end of CRUD for registration

# Parking lot registration routes using SQLAlchemy
@app.route('/registration_out', methods=['GET'])
def get_registration():
    # registrations is a list of tuples that looks like this [(ParkingLotRegistration1, Timeinterval1), (ParkingLotRegistration2, Timeinterval2).....]
    if current_user.role == "owner":
        registrations = db.session.query(ParkingLotRegistration, TimeInterval).join(TimeInterval, ParkingLotRegistration.id == TimeInterval.parking_lot_id).filter(ParkingLotRegistration.name == current_user.username).all() # users are allowed to see only his own data
    elif current_user.role == "admin":
        registrations = db.session.query(ParkingLotRegistration, TimeInterval).join(TimeInterval, ParkingLotRegistration.id == TimeInterval.parking_lot_id).all()
    else:
        return f"{current_user.username} is not allowed to view this page!"
    
    return render_template("registration_out.html", registrations=registrations)

# View parking lot area
@app.route('/show_parking_lot_area', methods=['GET'])
def get_parking_lot_area():
    area = parking_lot.area
    return render_template("show_parking_lot_area.html", area=area)

# link registration and parking lot area together
@app.route('/update', methods = ['GET'])
def update_data():
    all_set_back_to_empty_unbooked()
    link_reg_parking_lot()
    return f'parking lot update successful!'

# reset parking lot area back to its initial layout
@app.route('/reset_parking_lot', methods = ['GET'])
def reset_parking_lot():
    all_set_back_to_empty_unbooked()
    parking_lot.output_txt("parking_lot_in.txt")
    return "reset successful!"

# help borrowers find their match
@app.route('/demand', methods = ["GET"])
@login_required
def demand():
    if current_user.role != "borrower":
        return "non borrowers are not allowed to create demand record!"
    return render_template("demand.html", username = current_user.username)


@app.route('/create_borrower', methods = ["GET", "POST"])
@login_required
def create_borrower():
    name = request.form['name']
    start_time_str = request.form['start_time']
    end_time_str = request.form['end_time']
    
    # Convert strings to datetime objects
    start_time = datetime.fromisoformat(start_time_str)
    end_time = datetime.fromisoformat(end_time_str)

     # Create and add the new Borrower
    new_borrower = Borrower(
        name = name,
        start_time = start_time,
        end_time = end_time,
        user_id = current_user.id
    )
    db.session.add(new_borrower)
    db.session.commit()

    return "demand data added!"

@app.route('/query_demand', methods = ["GET", "POST"])
@login_required
def query_demand():
    if current_user.role == "borrower":
        demand_registrations = Borrower.query.filter(Borrower.name == current_user.username) # users are allowed to see only his own record
    elif current_user.role == "admin":
        demand_registrations = Borrower.query.all()
    return render_template('query_demand.html', demand_registrations = demand_registrations)

@app.route('/demand/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def update_demand(id):
    demand_registration = Borrower.query.get_or_404(id)
    
    if request.method == 'POST':
        # Update the demand registration details
        demand_registration.name = request.form['name']
        
        # Handle start time and end time
        start_time_str = request.form["start_time"]
        end_time_str = request.form["end_time"]
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        
        demand_registration.start_time = start_time
        demand_registration.end_time = end_time
        
        # Commit changes to the database
        db.session.commit()
        flash('Demand registration updated successfully!')
        return redirect(url_for('query_demand'))
    
    return render_template('edit_demand.html', demand_registration=demand_registration)
@app.route('/demand/delete/<int:id>', methods=['POST'])
@login_required
def delete_demand(id):
    demand_registration = Borrower.query.get_or_404(id)

    # Get associated information, if needed
    # (Adjust if there's related data to handle)

    db.session.delete(demand_registration)
    db.session.commit()

    flash('Demand registration deleted successfully!')
    return redirect(url_for('query_demand'))

@app.route('/match', methods=['GET', 'POST'])
@login_required
def match():
    if request.method == "POST":
        
        if current_user.role != "admin": # non admins are only allowed to access their own data
            role = current_user.role
            column_name = role + "_username"
            try:
                match_result = pd.read_excel("Match Result.xlsx")
            except:
                return render_template("match.html",data = {}) # retun empy data if admin does not specify algo
            else:
                user_record = match_result[match_result[column_name] == current_user.username]
                list_of_dictionaries = user_record.to_dict(orient="records")
                return render_template("match.html",data = list_of_dictionaries)
        

        elif current_user.role == "admin": # admins are allowed to access all data
            # firstly we make data ready
            knapsack_logic = importlib.import_module(name = "knapsack_logic")
            owner_df, borrower_df = knapsack_logic.create_data()
            matched_df_ff = knapsack_logic.first_fit_borrowers_to_owners_with_splitting(borrower_df, owner_df)
            matched_df_bf = knapsack_logic.best_fit_borrowers_to_owners_with_splitting(borrower_df, owner_df)
            stats_ff = knapsack_logic.statistics(matched_df = matched_df_ff, borrower_df = borrower_df.copy(), owner_df = owner_df.copy())
            stats_bf = knapsack_logic.statistics(matched_df = matched_df_bf, borrower_df = borrower_df.copy(), owner_df = owner_df.copy())
            
            if  request.form.get("choice") == "First Fit":
                list_of_dictionaries = matched_df_ff.to_dict(orient="records")
                # save as excel file
                matched_df_ff = pd.DataFrame(matched_df_ff)
                matched_df_ff.to_excel("Match Result.xlsx", index=False)
                return render_template("match.html",data = list_of_dictionaries, stats = stats_ff)
            elif request.form.get("choice") == "Best Fit":
                list_of_dictionaries = matched_df_bf.to_dict(orient="records")
                # save as excel file
                matched_df_bf = pd.DataFrame(matched_df_bf)
                matched_df_bf.to_excel("Match Result.xlsx", index=False)
                return render_template("match.html",data = list_of_dictionaries, stats= stats_bf)
            
    else: # if there is no info coming in, show original match.html
            return render_template("match.html")
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables within the application context
    app.run(debug=True) # scholl IP addr for display on other machines. set the argument to debug = True to initiate debug mode
