import os
import uuid  
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from app import supabase
from app.utils.decorators import login_required
from app.services.file_service import allowed_file, generate_unique_filename
from app.services.supabase_service import upload_file_to_supabase

galeria_bp = Blueprint('gallery', __name__, url_prefix='/galeria')

@galeria_bp.route('/', endpoint='index')
def public_gallery():
    """Exibe a galeria pública"""
    try:
        response = supabase.table('gallery_images')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(100)\
            .execute()
        images = response.data if response.data else []
    except Exception as e:
        print(f"Erro ao buscar imagens: {e}")
        images = []

    return render_template('galeria.html', images=images)  # <-- galeria pública

@galeria_bp.route('/admin', endpoint='admin')
@login_required
def admin_gallery():
    """Página administrativa para gerenciar imagens"""
    try:
        response = supabase.table('gallery_images')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(100)\
            .execute()
        images = response.data if response.data else []
    except Exception as e:
        print(f"Erro ao buscar imagens: {e}")
        images = []

    return render_template('admin/gallery.html', images=images)

@galeria_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload de imagem para galeria"""
    if request.method == 'POST':
        try:
            titulo = request.form.get('title')
            descricao = request.form.get('description', '')

            # Se não tiver título, gera um título aleatório
            if not titulo or titulo.strip() == '':
                titulo = f"Imagem-{uuid.uuid4().hex[:8]}"

            if 'file' not in request.files or not request.files['file'].filename:
                flash('Imagem é obrigatória.', 'error')
                return render_template('admin/upload_galeria.html')
            
            file = request.files['file']

            # Verificar extensão permitida
            if not allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'webp'}):
                flash('Tipo de imagem não permitido.', 'error')
                return render_template('admin/upload_galeria.html')

            filename = generate_unique_filename(file.filename)
            file_path = f"galeria/{filename}"

            upload_file_to_supabase(file, current_app.config['BUCKET_IMAGES'], file_path)
            file_url = supabase.storage.from_(current_app.config['BUCKET_IMAGES']).get_public_url(file_path)

            firebase_uid = session['user']['localId']
            author_email = session['user']['email']
            mime_type = file.content_type or 'image/jpeg'
            file_content = file.read()
            file_size = len(file_content)
            file.seek(0)

            image_data = {
                'titulo': titulo,
                'descricao': descricao,
                'file_path': file_url,
                'original_filename': file.filename,
                'file_size': file_size,
                'mime_type': mime_type,
                'firebase_author_uid': firebase_uid,
                'author_email': author_email,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            response = supabase.table('gallery_images').insert(image_data).execute()

            if response.data:
                flash('Imagem enviada com sucesso!', 'success')
                return redirect(url_for('gallery.index'))
            else:
                flash('Erro ao salvar imagem.', 'error')

        except Exception as e:
            print(f"Erro no upload: {e}")
            flash('Erro ao enviar imagem.', 'error')

    return render_template('admin/upload_galeria.html')


@galeria_bp.route('/delete/<uuid:image_id>', methods=['POST'])
@login_required
def delete(image_id):
    """Deleta imagem da galeria"""
    try:
        response = supabase.table('gallery_images').select('*').eq('id', str(image_id)).execute()
        if not response.data:
            flash('Imagem não encontrada.', 'error')
            return redirect(url_for('gallery.index'))

        image = response.data[0]
        current_user_uid = session['user']['localId']
        if image['firebase_author_uid'] != current_user_uid:
            flash('Você não tem permissão para deletar esta imagem.', 'error')
            return redirect(url_for('gallery.index'))

        try:
            file_url = image['file_path']
            if file_url and 'galeria/' in file_url:
                file_name = file_url.split('galeria/')[-1].split('?')[0]
                supabase.storage.from_(current_app.config['BUCKET_IMAGES']).remove([f"galeria/{file_name}"])
        except Exception as storage_e:
            print(f"Erro ao deletar imagem do storage: {storage_e}")

        delete_response = supabase.table('gallery_images').delete().eq('id', str(image_id)).execute()

        if delete_response.data:
            flash('Imagem deletada com sucesso.', 'success')
        else:
            flash('Erro ao deletar imagem.', 'error')

    except Exception as e:
        print(f"Erro ao deletar imagem: {e}")
        flash('Erro inesperado ao deletar.', 'error')

    return redirect(url_for('gallery.index'))
