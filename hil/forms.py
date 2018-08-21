from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SelectField, SubmitField, PasswordField
from wtforms.validators import InputRequired, Length


class TaskForm(FlaskForm):
    submit = SubmitField('Submit')
    file = SelectField(
            'Select file',
            validators=[InputRequired("Please select a file.")]
    )

    software = SelectField(
            'Select software',
            validators=[InputRequired("Please select a software.")]
    )

    def __init__(self, file_choices, sw_choices, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.file.choices = file_choices
        self.software.choices = sw_choices


class UserForm(FlaskForm):
    name = StringField(
            'NetID',
            validators=[InputRequired("Please enter your NetID.")]
    )
    password = PasswordField(
            'Password',
            validators=[InputRequired("Please enter your password."),
                        Length(min=6, message="Minimum 6 characters required for password.")]
    )
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        if kwargs.get('prefix'):
            self.submit.label.text = kwargs['prefix'].title()


class PasswordForm(FlaskForm):
    current_password = PasswordField(
            'Current Password',
            validators=[InputRequired("Please enter your current password.")]
    )

    new_password = PasswordField(
            'New Password',
            validators=[InputRequired("Please enter a new password."),
                        Length(min=6, message="Minimum 6 characters required for password.")]
    )
    submit = SubmitField('Change Password')


class FileForm(FlaskForm):
    file = FileField(validators=[FileRequired("Please select a filed.")])
    path = StringField('Upload to specific folder')
    submit = SubmitField('Upload')
