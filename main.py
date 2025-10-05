from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
import openai

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///telemedicine.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change in production
db = SQLAlchemy(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "doctor_login"

# -------------------------
# Models
# -------------------------
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    contact = db.Column(db.String(50), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    time = db.Column(db.String(50), nullable=False)

class AIConsult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    ai_advice = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)

class Doctor(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)  # plaintext for simplicity

# -------------------------
# Database setup
# -------------------------
with app.app_context():
    db.create_all()
    # Create default doctor if not exists
    if not Doctor.query.filter_by(username="drkhan").first():
        doctor = Doctor(username="drkhan", password="password123")
        db.session.add(doctor)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return Doctor.query.get(int(user_id))

# -------------------------
# Routes
# -------------------------
@app.route("/")
def home():
    return render_template("index.html", message="Welcome to your Virtual Heart Care Assistant!")

# -------------------------
# Doctor Login
# -------------------------
@app.route("/doctor/login", methods=["GET", "POST"])
def doctor_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        doctor = Doctor.query.filter_by(username=username, password=password).first()
        if doctor:
            login_user(doctor)
            return redirect(url_for("doctor_dashboard"))
        else:
            flash("Invalid credentials")
    return render_template("doctor_login.html")

# -------------------------
# Doctor Logout
# -------------------------
@app.route("/doctor/logout")
@login_required
def doctor_logout():
    logout_user()
    return redirect(url_for("home"))

# -------------------------
# Patient Registration
# -------------------------
@app.route("/patient/register", methods=["GET", "POST"])
def register_patient():
    if request.method == "POST":
        patient = Patient(
            name=request.form["name"],
            age=request.form["age"],
            gender=request.form["gender"],
            contact=request.form["contact"]
        )
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("patient_form.html")

# -------------------------
# Appointment Booking
# -------------------------
@app.route("/appointment/book", methods=["GET", "POST"])
def book_appointment():
    if request.method == "POST":
        appt = Appointment(
            patient_name=request.form["patient_name"],
            time=request.form["time"]
        )
        db.session.add(appt)
        db.session.commit()
        return redirect(url_for("doctor_dashboard"))
    return render_template("appointment_form.html")

# -------------------------
# AI Symptom Checker with personalized advice
# -------------------------
@app.route("/ai/consult/form", methods=["GET", "POST"])
def ai_consult():
    advice = prescription = recommendations = None
    patient_name = request.form.get("patient_name", "Anonymous")
    
    if request.method == "POST":
        question = request.form["question"]
        try:
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful AI doctor specialized in heart diseases. Provide a clear answer, a suggested prescription, and lifestyle recommendations if needed."},
                    {"role": "user", "content": f"Patient: {patient_name}, Symptom/Question: {question}"}
                ]
            )
            content = response.choices[0].message["content"]
            
            # Simple parsing (split content into advice/prescription/recommendations)
            # AI should return in format: Advice | Prescription | Recommendations
            try:
                advice, prescription, recommendations = [s.strip() for s in content.split("|")]
            except:
                advice = content
                prescription = "Not provided"
                recommendations = "Not provided"

        except Exception as e:
            advice = f"Error: {str(e)}"
            prescription = "Error"
            recommendations = "Error"

        # Save consultation
        consult = AIConsult(
            patient_name=patient_name,
            question=question,
            ai_advice=advice,
            prescription=prescription,
            recommendations=recommendations
        )
        db.session.add(consult)
        db.session.commit()

    previous_consults = AIConsult.query.filter_by(patient_name=patient_name).all()
    return render_template("ai_consult.html", advice=advice, prescription=prescription, recommendations=recommendations, previous_consults=previous_consults)

# -------------------------
# Doctor Dashboard
# -------------------------
@app.route("/doctor/dashboard")
@login_required
def doctor_dashboard():
    appointments = Appointment.query.all()
    consults = AIConsult.query.all()
    return render_template("doctor_dashboard.html", appointments=appointments, consults=consults)

# -------------------------
# Delete Appointment
# -------------------------
@app.route("/doctor/appointment/delete/<int:appt_id>")
@login_required
def delete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    db.session.delete(appt)
    db.session.commit()
    return redirect(url_for("doctor_dashboard"))

# -------------------------
# Run App
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
