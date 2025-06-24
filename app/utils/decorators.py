"""
Custom decorators for the application.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, g

def login_required(f):
    """
    Decorator to ensure a user is logged in before accessing a route.

    If the user is not logged in (i.e., 'user' not in session),
    they are redirected to the login page.

    Args:
        f (function): The view function to decorate.

    Returns:
        function: The decorated view function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
