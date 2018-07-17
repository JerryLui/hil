from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, PasswordField
from wtforms.validators import InputRequired


class TaskForm(FlaskForm):
    submit = SubmitField('Submit')

    def __init__(self, files):
        self.file_name = SelectField(
                'Select file',
                choices=[(file.name, file.name) for file in files],
                validators=[InputRequired("Please select a file.")]
        )
        super().__init__()


class RegisterForm(FlaskForm):
    register_name = StringField(
            'NetID',
            validators=[InputRequired("Please enter your NetID.")]
    )
    register_password = PasswordField(
            'Password',
            validators=[InputRequired("Please enter your password.")]
    )
    register_submit = SubmitField('Register')


class LoginForm(FlaskForm):
    login_name = StringField(
            'NetID',
            validators=[InputRequired("Please enter your NetID.")]
    )
    login_password = PasswordField(
            'Password',
            validators=[InputRequired("Please enter your password.")]
    )
    login_submit = SubmitField('Log In')
