from datetime import date
from typing import Optional
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, Length, ValidationError, Optional, InputRequired
from app.models.machine import Machine


MACHINE_STATUS_CHOICES = [
    ("running", "Running"),
    ("idle", "Idle"),
    ("maintenance", "Maintenance"),
    ("offline", "Offline"),
]

SENSOR_TYPE_CHOICES = [
    ("temperature", "Temperature"),
    ("vibration", "Vibration"),
    ("current", "Current"),
    ("voltage", "Voltage"),
    ("pressure", "Pressure"),
    ("humidity", "Humidity"),
    ("speed", "Speed"),
]


class MachineForm(FlaskForm):
    machine_name = StringField("Machine Name", validators=[DataRequired(), Length(max=120)])
    machine_type = StringField("Machine Type", validators=[DataRequired(), Length(max=120)])
    location = StringField("Location", validators=[Optional(), Length(max=120)])
    installation_date = DateField(
        "Installation Date", validators=[Optional()], format="%Y-%m-%d", default=date.today
    )
    status = SelectField("Status", choices=MACHINE_STATUS_CHOICES, validators=[DataRequired()])
    submit = SubmitField("Save")

    def __init__(self, company_id: int, machine: Optional[Machine] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_id = company_id
        self.machine = machine

    def validate_machine_name(self, field):
        name = field.data.strip()
        query = Machine.query.filter_by(company_id=self.company_id, machine_name=name)
        if self.machine:
            query = query.filter(Machine.id != self.machine.id)
        if query.first():
            raise ValidationError("Machine name must be unique within your company.")


class SensorForm(FlaskForm):
    sensor_type = SelectField("Sensor Type", choices=SENSOR_TYPE_CHOICES, validators=[DataRequired()])
    unit = StringField("Unit", validators=[DataRequired(), Length(max=20)])
    min_threshold = FloatField("Min Threshold", validators=[InputRequired()])
    max_threshold = FloatField("Max Threshold", validators=[InputRequired()])
    submit = SubmitField("Save")

    def validate_max_threshold(self, field):
        if self.min_threshold.data is not None and field.data is not None:
            if field.data <= self.min_threshold.data:
                raise ValidationError("Max threshold must be greater than min threshold.")
