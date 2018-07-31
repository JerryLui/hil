from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SelectField, SubmitField, PasswordField
from wtforms.validators import InputRequired, Length


class TaskForm(FlaskForm):
    submit = SubmitField('Submit')
    file_name = SelectField(
            'Select file',
            validators=[InputRequired("Please select a file.")]
    )

    def __init__(self, choices, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.file_name.choices = choices


class PasswordForm(FlaskForm):
    password = PasswordField(
            'Password',
            validators=[InputRequired("Please enter your password."),
                        Length(min=6, message="Minimum 6 characters required for password.")]
    )
    submit = SubmitField('Change password')

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


class FileForm(FlaskForm):
    file = FileField(validators=[FileRequired("Please select a filed.")])
    submit = SubmitField('Upload')
