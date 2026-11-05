from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import StringField, PasswordField, TextAreaField, SelectField, SelectMultipleField, DateField, DateTimeLocalField, TimeField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange, Regexp
from wtforms.widgets import CheckboxInput, ListWidget
from wtforms.validators import ValidationError
from email_validator import validate_email, EmailNotValidError


def email_address(form, field):
    # .test addresses are deliberately used for offline academic demo accounts.
    try:
        validate_email(field.data, check_deliverability=False, test_environment=True)
    except EmailNotValidError:
        raise ValidationError("Enter a valid email address.")


class ActionForm(FlaskForm):
    """CSRF form for service actions; service functions validate their payloads."""


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), email_address, Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=200)])


class RegisterForm(LoginForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField("Phone number", validators=[Optional(), Regexp(r"^\+?[0-9 ()-]{7,25}$", message="Enter a valid phone number (7–25 characters).")])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField("Phone number", validators=[Optional(), Regexp(r"^\+?[0-9 ()-]{7,25}$")])
    address = TextAreaField("Address", validators=[Optional(), Length(max=500)])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    preferred_contact = SelectField("Preferred contact", choices=[("Email", "Email"), ("Phone", "Phone")])


class DeviceForm(FlaskForm):
    nickname = StringField("Device nickname", validators=[DataRequired(), Length(min=2, max=100)])
    device_model_id = SelectField("Brand and model", coerce=int, validators=[DataRequired()])
    serial_number = StringField("Serial number", validators=[Optional(), Length(max=100)])
    purchase_date = DateField("Purchase date", validators=[Optional()])
    notes = TextAreaField("Device notes", validators=[Optional(), Length(max=2000)])


class SymptomCheckbox(CheckboxInput):
    def __call__(self, field, **kwargs):
        # DataRequired means at least one choice on the server. Applying HTML's
        # required flag to each checkbox would incorrectly require ALL symptoms.
        kwargs["required"] = False
        return super().__call__(field, **kwargs)


class SymptomChoices(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = SymptomCheckbox()


class DiagnosisForm(FlaskForm):
    device_id = SelectField("Your device", coerce=int, validators=[DataRequired()])
    symptom_ids = SymptomChoices("What are you experiencing?", coerce=int, validators=[DataRequired(message="Select at least one symptom.")])


class RequestForm(DiagnosisForm):
    service_center_id = SelectField("Service centre", coerce=int, validators=[DataRequired()])
    issue_description = TextAreaField("Tell us about the issue", validators=[DataRequired(), Length(min=10, max=5000)])
    urgency = SelectField("Priority", choices=[("Normal", "Normal"), ("High", "High"), ("Urgent", "Urgent")])
    attachment = FileField("Photo or PDF (optional, maximum 5 MB)", validators=[FileAllowed(["jpg", "jpeg", "png", "webp", "pdf"])])


class AppointmentForm(FlaskForm):
    repair_request_id = SelectField("Repair request", coerce=int, validators=[DataRequired()])
    service_center_id = SelectField("Service centre", coerce=int, validators=[DataRequired()])
    scheduled_start = DateTimeLocalField("Start time (Pakistan time)", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    scheduled_end = DateTimeLocalField("End time (Pakistan time)", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])


class AvailabilityForm(FlaskForm):
    available_date = DateField("Date", validators=[DataRequired()])
    start_time = TimeField("From", validators=[DataRequired()])
    end_time = TimeField("Until", validators=[DataRequired()])


class ReviewForm(FlaskForm):
    rating = SelectField("How was your repair?", coerce=int, choices=[(5, "5 — Excellent"), (4, "4 — Good"), (3, "3 — Okay"), (2, "2 — Poor"), (1, "1 — Very poor")])
    comment = TextAreaField("Your feedback", validators=[Optional(), Length(max=2000)])
