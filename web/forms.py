from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SelectField, SubmitField, PasswordField
from wtforms.validators import InputRequired


class TaskForm(FlaskForm):
    submit = SubmitField('Submit')
    file_name = SelectField(
            'Select file',
            validators=[InputRequired("Please select a file.")]
    )

    def __init__(self, choices, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.file_name.choices = choices


class UserForm(FlaskForm):
    name = StringField(
            'NetID',
            validators=[InputRequired("Please enter your NetID.")]
    )
    password = PasswordField(
            'Password',
            validators=[InputRequired("Please enter your password.")]
    )
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)


class FileForm(FlaskForm):
    file = FileField(validators=[FileRequired("Please select a filed.")])
