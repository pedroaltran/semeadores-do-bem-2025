"""
Service functions for user-related operations (e.g., profile management).
"""
from datetime import datetime, timezone
from flask import current_app
from app import supabase

def get_or_create_user_profile(firebase_user):
    """Cria ou atualiza o perfil do usuário no Supabase baseado no Firebase"""
    try:
        firebase_uid = firebase_user.get('localId')
        email = firebase_user.get('email')
        
        # Verificar se o perfil já existe
        response = supabase.table('user_profiles').select('*').eq('firebase_uid', firebase_uid).execute()
        
        if response.data:
            # Atualizar último login
            supabase.table('user_profiles').update({
                'last_login': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('firebase_uid', firebase_uid).execute()
            return response.data[0]
        else:
            # Criar novo perfil - só admin pré-definido pode ser criado
            is_admin = email in ['pedroaltran@gmail.com', 'admin@semeadoresdebem.org.br']
            
            profile_data = {
                'firebase_uid': firebase_uid,
                'email': email,
                'is_admin': is_admin,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_login': datetime.now(timezone.utc).isoformat()
            }
            
            insert_response = supabase.table('user_profiles').insert(profile_data).execute()
            return insert_response.data[0] if insert_response.data else None
            
    except Exception as e:
        current_app.logger.error(f"Erro ao gerenciar perfil do usuário: {e}")
        return None
