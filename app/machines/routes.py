from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.extensions import db
from app.audit import log_action
from app.decorators import role_required, manager_required, admin_required
from app.models.machine import Machine
from app.models.sensor import Sensor
from app.models.machine_data import get_latest_machine_data
from app.security import get_active_company_id
from . import machines_bp
from .forms import MachineForm, SensorForm


def _get_machine_or_404(machine_id: int) -> Machine:
    company_id = get_active_company_id()
    return Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()


def _get_sensor_or_404(machine_id: int, sensor_id: int) -> Sensor:
    company_id = get_active_company_id()
    return (
        Sensor.query.join(Machine)
        .filter(
            Sensor.id == sensor_id,
            Sensor.machine_id == machine_id,
            Machine.company_id == company_id,
        )
        .first_or_404()
    )


@machines_bp.route("/")
@login_required
@role_required("admin", "manager", "viewer")
def list_machines():
    search = request.args.get("q", "").strip()
    company_id = get_active_company_id()
    query = Machine.query.filter_by(company_id=company_id)
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            or_(
                Machine.machine_name.ilike(like_term),
                Machine.machine_type.ilike(like_term),
                Machine.location.ilike(like_term),
            )
        )
    machines = query.order_by(Machine.created_at.desc()).all()
    return render_template("machines/list.html", machines=machines, search=search)


@machines_bp.route("/create", methods=["GET", "POST"])
@login_required
@manager_required
def create_machine():
    company_id = get_active_company_id()
    form = MachineForm(company_id=company_id)
    if form.validate_on_submit():
        machine = Machine(
            machine_name=form.machine_name.data.strip(),
            machine_type=form.machine_type.data.strip(),
            location=form.location.data.strip() if form.location.data else None,
            installation_date=form.installation_date.data,
            status=form.status.data,
            company_id=company_id,
        )
        db.session.add(machine)
        db.session.flush()
        log_action(
            action="machine_created",
            entity_type="machine",
            entity_id=machine.id,
            old_value=None,
            new_value={
                "machine_name": machine.machine_name,
                "machine_type": machine.machine_type,
                "location": machine.location,
                "status": machine.status,
            },
        )
        db.session.commit()
        flash("Machine created successfully.", "success")
        return redirect(url_for("machines.list_machines"))

    return render_template("machines/create.html", form=form)


@machines_bp.route("/<int:machine_id>")
@login_required
@role_required("admin", "manager", "viewer")
def machine_detail(machine_id):
    machine = _get_machine_or_404(machine_id)
    sensors = machine.sensors.order_by(Sensor.created_at.desc()).all()
    return render_template("machines/detail.html", machine=machine, sensors=sensors)


@machines_bp.route("/<int:machine_id>/edit", methods=["GET", "POST"])
@login_required
@manager_required
def edit_machine(machine_id):
    machine = _get_machine_or_404(machine_id)
    form = MachineForm(company_id=machine.company_id, machine=machine, obj=machine)
    if form.validate_on_submit():
        old_value = {
            "machine_name": machine.machine_name,
            "machine_type": machine.machine_type,
            "location": machine.location,
            "installation_date": machine.installation_date.isoformat() if machine.installation_date else None,
            "status": machine.status,
        }
        machine.machine_name = form.machine_name.data.strip()
        machine.machine_type = form.machine_type.data.strip()
        machine.location = form.location.data.strip() if form.location.data else None
        machine.installation_date = form.installation_date.data
        machine.status = form.status.data

        new_value = {
            "machine_name": machine.machine_name,
            "machine_type": machine.machine_type,
            "location": machine.location,
            "installation_date": machine.installation_date.isoformat() if machine.installation_date else None,
            "status": machine.status,
        }
        log_action(
            action="machine_updated",
            entity_type="machine",
            entity_id=machine.id,
            old_value=old_value,
            new_value=new_value,
        )
        db.session.commit()
        flash("Machine updated successfully.", "success")
        return redirect(url_for("machines.list_machines"))

    return render_template("machines/edit.html", form=form, machine=machine)


@machines_bp.route("/<int:machine_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_machine(machine_id):
    machine = _get_machine_or_404(machine_id)
    old_value = {
        "machine_name": machine.machine_name,
        "machine_type": machine.machine_type,
        "location": machine.location,
        "installation_date": machine.installation_date.isoformat() if machine.installation_date else None,
        "status": machine.status,
    }
    db.session.delete(machine)
    log_action(
        action="machine_deleted",
        entity_type="machine",
        entity_id=machine.id,
        old_value=old_value,
        new_value=None,
    )
    db.session.commit()
    flash("Machine deleted successfully.", "info")
    return redirect(url_for("machines.list_machines"))


@machines_bp.route("/<int:machine_id>/sensor/add", methods=["GET", "POST"])
@login_required
@manager_required
def add_sensor(machine_id):
    machine = _get_machine_or_404(machine_id)
    form = SensorForm()
    if form.validate_on_submit():
        sensor = Sensor(
            machine_id=machine.id,
            sensor_type=form.sensor_type.data,
            unit=form.unit.data.strip(),
            min_threshold=form.min_threshold.data,
            max_threshold=form.max_threshold.data,
        )
        db.session.add(sensor)
        db.session.flush()
        log_action(
            action="sensor_added",
            entity_type="sensor",
            entity_id=sensor.id,
            old_value=None,
            new_value={
                "machine_id": machine.id,
                "sensor_type": sensor.sensor_type,
                "unit": sensor.unit,
                "min_threshold": sensor.min_threshold,
                "max_threshold": sensor.max_threshold,
            },
        )
        db.session.commit()
        flash("Sensor added successfully.", "success")
        return redirect(url_for("machines.machine_detail", machine_id=machine.id))

    return render_template("machines/sensor_form.html", form=form, machine=machine, is_edit=False)


@machines_bp.route("/<int:machine_id>/sensor/<int:sensor_id>/edit", methods=["GET", "POST"])
@login_required
@manager_required
def edit_sensor(machine_id, sensor_id):
    machine = _get_machine_or_404(machine_id)
    sensor = _get_sensor_or_404(machine_id, sensor_id)
    form = SensorForm(obj=sensor)
    if form.validate_on_submit():
        old_value = {
            "sensor_type": sensor.sensor_type,
            "unit": sensor.unit,
            "min_threshold": sensor.min_threshold,
            "max_threshold": sensor.max_threshold,
        }
        sensor.sensor_type = form.sensor_type.data
        sensor.unit = form.unit.data.strip()
        sensor.min_threshold = form.min_threshold.data
        sensor.max_threshold = form.max_threshold.data
        new_value = {
            "sensor_type": sensor.sensor_type,
            "unit": sensor.unit,
            "min_threshold": sensor.min_threshold,
            "max_threshold": sensor.max_threshold,
        }
        log_action(
            action="sensor_updated",
            entity_type="sensor",
            entity_id=sensor.id,
            old_value=old_value,
            new_value=new_value,
        )
        db.session.commit()
        flash("Sensor updated successfully.", "success")
        return redirect(url_for("machines.machine_detail", machine_id=machine.id))

    return render_template("machines/sensor_form.html", form=form, machine=machine, is_edit=True)


@machines_bp.route("/<int:machine_id>/sensor/<int:sensor_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_sensor(machine_id, sensor_id):
    machine = _get_machine_or_404(machine_id)
    sensor = _get_sensor_or_404(machine_id, sensor_id)
    old_value = {
        "sensor_type": sensor.sensor_type,
        "unit": sensor.unit,
        "min_threshold": sensor.min_threshold,
        "max_threshold": sensor.max_threshold,
    }
    db.session.delete(sensor)
    log_action(
        action="sensor_deleted",
        entity_type="sensor",
        entity_id=sensor.id,
        old_value=old_value,
        new_value=None,
    )
    db.session.commit()
    flash("Sensor deleted successfully.", "info")
    return redirect(url_for("machines.machine_detail", machine_id=machine.id))


@machines_bp.route("/<int:machine_id>/live")
@login_required
@role_required("admin", "manager", "viewer")
def machine_live(machine_id):
    machine = _get_machine_or_404(machine_id)
    latest = get_latest_machine_data(machine.id)
    return render_template("machines/live.html", machine=machine, latest=latest)


@machines_bp.route("/<int:machine_id>/live-data")
@login_required
@role_required("admin", "manager", "viewer")
def machine_live_data(machine_id):
    machine = _get_machine_or_404(machine_id)
    latest = get_latest_machine_data(machine.id)
    response = {
        "machine_id": machine.id,
        "machine_name": machine.machine_name,
        "status": machine.status,
        "last_seen": machine.last_seen.isoformat() if machine.last_seen else None,
        "latest": None,
    }

    if latest:
        response["latest"] = {
            "timestamp": latest.timestamp.isoformat(),
            "temperature": latest.temperature,
            "vibration": latest.vibration,
            "current": latest.current,
            "voltage": latest.voltage,
            "pressure": latest.pressure,
            "humidity": latest.humidity,
            "speed": latest.speed,
            "running_status": latest.running_status,
        }

    return response
