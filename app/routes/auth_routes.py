"""
Authentication routes (login, logout, user management).
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from app import auth
from app.services.user_service import get_or_create_user_profile
from app.utils.decorators import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email') or request.form.get('username')
        password = request.form.get('password')
        
        try:
            # Autenticar com Firebase
            user = auth.sign_in_with_email_and_password(email, password)
            
            # Criar/atualizar perfil no Supabase
            profile = get_or_create_user_profile(user)
            
            session['user'] = {
                'token': user['idToken'],
                'email': user['email'],
                'localId': user['localId']
            }
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            print(f"Erro no login: {e}")
            return render_template('login.html', error="Falha no login. Verifique suas credenciais.")
    
    return render_template('login.html')

@auth_bp.route('/me')
def me():
    user = session.get('user')
    if user:
        return jsonify({'email': user['email'], 'localId': user['localId']})
    else:
        return jsonify({'email': None}), 401

@auth_bp.route('/logout')
@login_required
def logout():
    try:
        # Logout do Firebase
        auth.current_user = None
    except Exception as e:
        print(f"Erro no logout: {e}")
    
    session.pop('user', None)
    return redirect(url_for('auth.login'))
