from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length


class TaskForm(FlaskForm):
    submit = SubmitField('Submit')

    def __init__(self, files):
        self.file_name = SelectField(
                'Select file',
                choices=[(file.name, file.name) for file in files],
                validators=[DataRequired("Please select a file.")]
        )
        super().__init__()


class RegisterForm(FlaskForm):
    user_name = StringField(
            'NetID',
            validators=[DataRequired("Please enter your NetID."),
                        Length(min=6, max=6, message='NetID has a length of 6 characters.')]
    )
    user_password = PasswordField(
            'Password',
            validators=[DataRequired("Please enter your password.")]
    )
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    user_name = StringField(
            'NetID',
            validators=[DataRequired("Please enter your NetID."),
                        Length(min=6, max=6, message='NetID has a length of 6 characters.')]
    )
    user_password = PasswordField(
            'Password',
            validators=[DataRequired("Please enter your password.")]
    )
    submit = SubmitField('Log In')
