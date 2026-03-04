from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import User


class RegistrationForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    company_name = StringField("Company Name", validators=[DataRequired(), Length(min=2, max=120)])
    role = SelectField(
        "Role",
        choices=[
            ("ENTERPRISE_ADMIN", "Enterprise Admin"),
            ("PLANT_MANAGER", "Plant Manager"),
            ("VIEWER", "Viewer"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email is already registered.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")
