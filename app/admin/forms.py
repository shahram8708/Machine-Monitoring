from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app.models.company import Company
from app.models.plant import Plant
from app.models.user import User

ROLE_CHOICES = [
    ("SUPER_ADMIN", "Super Admin"),
    ("ENTERPRISE_ADMIN", "Enterprise Admin"),
    ("PLANT_MANAGER", "Plant Manager"),
    ("MAINTENANCE_HEAD", "Maintenance Head"),
    ("TECHNICIAN", "Technician"),
    ("VIEWER", "Viewer"),
]


class AdminUserInlineForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField("Role", choices=ROLE_CHOICES, validators=[DataRequired()])
    company_id = SelectField("Company", coerce=int, validators=[DataRequired()])
    plant_id = SelectField("Plant", coerce=int, validators=[Optional()])
    submit_create = SubmitField("Add User")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        companies = Company.query.order_by(Company.company_name).all()
        self.company_id.choices = [(c.id, c.company_name) for c in companies]
        plants = Plant.query.order_by(Plant.name).all()
        self.plant_id.choices = [(0, "Optional")] + [(p.id, p.name) for p in plants]

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data.lower()).first()
        if existing:
            raise ValidationError("Email already exists")


class CSVUploadForm(FlaskForm):
    company_id = SelectField("Company", coerce=int, validators=[DataRequired()])
    file = FileField("Upload CSV", validators=[FileRequired(), FileAllowed(["csv"], "CSV only")])
    submit_upload = SubmitField("Upload CSV")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        companies = Company.query.order_by(Company.company_name).all()
        self.company_id.choices = [(c.id, c.company_name) for c in companies]


class AdminUserForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField("Role", choices=ROLE_CHOICES, validators=[DataRequired()])
    company_id = SelectField("Company", coerce=int, validators=[DataRequired()])
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=128)])
    active = BooleanField("Active", default=True)
    submit = SubmitField("Save")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_id.choices = [(c.id, c.company_name) for c in Company.query.order_by(Company.company_name).all()]

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data.lower()).first()
        if existing and getattr(self, "user_id", None) != existing.id:
            raise ValidationError("Email already exists")
