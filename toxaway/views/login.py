#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import redirect, render_template, session, url_for, flash

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired

from toxaway.models.profile import Profile

import logging
logger = logging.getLogger(__name__)

__all__ = [ 'register' ]

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class __LoginForm__(FlaskForm) :
    profile_name = StringField('Profile Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    create_flag = BooleanField('Create')
    submit = SubmitField('Login')

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class login_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        form = __LoginForm__()
        if form.validate_on_submit() :
            profile = Profile.load(self.config, form.profile_name.data, form.password.data)
            if profile is None :
                if form.create_flag.data :
                    logger.info('loaded requested profile')
                    profile = Profile.create(self.config, form.profile_name.data, form.password.data)
                else :
                    logger.info('failed to locate requested profile')
                    return render_template('login.html', title='Login', form=form)

            # i cannot believe that this is secure, but given that
            # the user is the one who sent the password...
            session['profile_name'] = form.profile_name.data
            session['profile_secret'] = form.password.data

            return redirect(url_for('index_app'))
        else :
            return render_template('login.html', title='Login', form=form)

## ----------------------------------------------------------------
## ----------------------------------------------------------------
class logout_app(object) :
    def __init__(self, config) :
        self.__name__ = type(self).__name__
        self.config = config

    def __call__(self, *args) :
        session.pop('profile_name', None)
        session.pop('profile_secret', None)

        return redirect(url_for('index_app'))

## ----------------------------------------------------------------
## ----------------------------------------------------------------
def register(app, config) :
    logging.info('register auth apps')
    app.add_url_rule('/login', None, login_app(config), methods=['GET', 'POST'])
    app.add_url_rule('/logout', None, logout_app(config))
