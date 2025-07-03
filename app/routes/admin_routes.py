"""
Admin routes (dashboard, statistics, content management).
"""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import supabase
from app.utils.decorators import login_required

admin_bp = Blueprint('admin', __name__)

def set_user_context():
    """Define o contexto do usuário Firebase para RLS"""
    if 'user' in session:
        try:
            supabase.rpc('set_firebase_user_context', {'firebase_uid': session['user']['localId']}).execute()
        except Exception as e:
            print(f"Erro ao definir contexto do usuário: {e}")
            # Continua mesmo se falhar, pois pode não ser crítico para todas as operações

@admin_bp.route('/')
@login_required
def dashboard():
    """Dashboard principal do admin"""
    try:
        # Definir contexto do usuário para RLS
        set_user_context()
        
        # Estatísticas básicas
        stats = {}
        
        # Total de posts
        posts_response = supabase.table('blog_posts').select('id').execute()
        stats['total_posts'] = len(posts_response.data) if posts_response.data else 0
        
        # Posts publicados
        published_response = supabase.table('blog_posts').select('id').eq('status', 'published').execute()
        stats['published_posts'] = len(published_response.data) if published_response.data else 0
        
        # Total de documentos
        docs_response = supabase.table('transparency_documents').select('id').execute()
        stats['total_documents'] = len(docs_response.data) if docs_response.data else 0

        # Total de fotos na galeria
        fotos_response = supabase.table('gallery_images').select('id').execute()
        stats['total_fotos'] = len(fotos_response.data) if fotos_response.data else 0

        # Imagens recentes da galeria
        gallery_response = supabase.table('gallery_images').select('*').order('created_at', desc=True).limit(5).execute()
        recent_images = [
            {
                'id': img['id'],
                'url': img['file_path'],
                'name': img.get('titulo') or img.get('original_filename', 'sem_titulo')
            }
            for img in gallery_response.data
        ] if gallery_response.data else []

        
        # Mensagens não lidas
        messages_response = supabase.table('contact_messages').select('id').eq('status', 'nova').execute()
        stats['unread_messages'] = len(messages_response.data) if messages_response.data else 0
        
        # Posts recentes
        recent_posts_response = supabase.table('blog_posts').select('*').order('created_at', desc=True).limit(5).execute()
        recent_posts = recent_posts_response.data if recent_posts_response.data else []
        
        # Mensagens recentes
        recent_messages_response = supabase.table('contact_messages').select('*').order('created_at', desc=True).limit(5).execute()
        recent_messages = recent_messages_response.data if recent_messages_response.data else []
        
        # Documentos recentes
        recent_documents_response = supabase.table('transparency_documents').select('*').order('created_at', desc=True).limit(5).execute()
        recent_documents = recent_documents_response.data if recent_documents_response.data else []
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        stats = {'total_posts': 0, 'published_posts': 0, 'total_documents': 0, 'unread_messages': 0}
        recent_posts = []
        recent_messages = []
        recent_documents = []
        recent_images = []
    
    return render_template('admin/dashboard.html', 
                           stats=stats,
                           recent_posts=recent_posts,
                           recent_messages=recent_messages,
                           recent_documents=recent_documents,
                           recent_images=recent_images)

@admin_bp.route('/messages')
@login_required
def messages():
    """Gerenciar mensagens de contato"""
    set_user_context()
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    per_page = 10
    offset = (page - 1) * per_page
    
    try:
        # Construir query baseada no filtro
        query = supabase.table('contact_messages').select('*')
        
        if status_filter != 'all':
            query = query.eq('status', status_filter)
        
        response = query.order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        messages = response.data if response.data else []
        
        # Contar total
        count_query = supabase.table('contact_messages').select('id')
        if status_filter != 'all':
            count_query = count_query.eq('status', status_filter)
        
        count_response = count_query.execute()
        total_messages = len(count_response.data) if count_response.data else 0
        
        has_next = total_messages > (page * per_page)
        has_prev = page > 1
        
    except Exception as e:
        print(f"Erro ao buscar mensagens: {e}")
        messages = []
        has_next = False
        has_prev = False
    
    return render_template('admin/messages.html', 
                           messages=messages,
                           page=page,
                           has_next=has_next,
                           has_prev=has_prev,
                           status_filter=status_filter)

@admin_bp.route('/messages/<message_id>/mark-read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    """Marcar mensagem como lida"""
    set_user_context()
    
    try:
        response = supabase.table('contact_messages').update({
            'status': 'lida',
            'read_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', message_id).execute()
        
        if response.data:
            flash('Mensagem marcada como lida.', 'success')
        else:
            flash('Erro ao atualizar mensagem.', 'error')
            
    except Exception as e:
        print(f"Erro ao marcar mensagem como lida: {e}")
        flash('Erro ao atualizar mensagem.', 'error')
    
    return redirect(url_for('admin.messages'))

@admin_bp.route('/messages/<message_id>/delete', methods=['POST'])
@login_required
def delete_message(message_id):
    """Deletar mensagem de contato"""
    set_user_context()
    
    try:
        response = supabase.table('contact_messages').delete().eq('id', message_id).execute()
        
        if response.data:
            flash('Mensagem deletada com sucesso.', 'success')
        else:
            flash('Erro ao deletar mensagem.', 'error')
            
    except Exception as e:
        print(f"Erro ao deletar mensagem: {e}")
        flash('Erro ao deletar mensagem.', 'error')
    
    return redirect(url_for('admin.messages'))

@admin_bp.route('/documents')
@login_required
def documents():
    """Gerenciar documentos de transparência"""
    set_user_context()
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    try:
        response = supabase.table('transparency_documents').select('*').order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        documents = response.data if response.data else []
        
        # Contar total
        count_response = supabase.table('transparency_documents').select('id').execute()
        total_documents = len(count_response.data) if count_response.data else 0
        
        has_next = total_documents > (page * per_page)
        has_prev = page > 1
        
    except Exception as e:
        print(f"Erro ao buscar documentos: {e}")
        documents = []
        has_next = False
        has_prev = False
    
    return render_template('admin/documents.html', 
                           documents=documents,
                           page=page,
                           has_next=has_next,
                           has_prev=has_prev)