"""
Transparency routes (document listing, upload, download, deletion).
"""
import os
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, session
from werkzeug.utils import secure_filename
from app import supabase
from app.utils.decorators import login_required
from app.services.file_service import allowed_file, generate_unique_filename
from app.services.supabase_service import upload_file_to_supabase

transparency_bp = Blueprint('transparency', __name__)

@transparency_bp.route('/')
def index():
    """Lista documentos de transparência"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    try:
        response = supabase.table('transparency_documents').select('*').order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        documents = response.data if response.data else []
        
        # Contar total
        count_response = supabase.table('transparency_documents').select('id', count='exact').execute()
        total_documents = count_response.count if count_response.count else 0
        
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

@transparency_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload de documento de transparência"""
    if request.method == 'POST':
        try:
            titulo = request.form.get('title')  # HTML usa 'title', banco usa 'titulo'
            descricao = request.form.get('description', '')  # HTML usa 'description', banco usa 'descricao'
            categoria = request.form.get('category', 'geral')  # HTML usa 'category', banco usa 'categoria'
            
            if not titulo:
                flash('Título é obrigatório.', 'error')
                return render_template('admin/upload.html')
            
            # Verificar se arquivo foi enviado
            if 'file' not in request.files or not request.files['file'].filename:
                flash('Arquivo é obrigatório.', 'error')
                return render_template('admin/upload.html')
            
            file = request.files['file']
            
            # Validar tipo de arquivo
            if not allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS_PDF']):
                flash('Tipo de arquivo não permitido. Use PDF, DOC, DOCX, XLS ou XLSX.', 'error')
                return render_template('admin/upload.html')
            
            # Gerar nome único para o arquivo
            filename = generate_unique_filename(file.filename)
            file_path = f"documents/{filename}"
            
            # Upload para Supabase Storage
            upload_file_to_supabase(file, current_app.config['BUCKET_DOCUMENTS'], file_path)
            
            # Obter URL pública (será salva em file_path no banco)
            file_url = supabase.storage.from_(current_app.config['BUCKET_DOCUMENTS']).get_public_url(file_path)
            
            # Obter dados do usuário
            firebase_uid = session['user']['localId']
            author_email = session['user']['email']
            
            # Obter tamanho do arquivo
            file_content = file.read()
            file_size = len(file_content)
            file.seek(0)  # Resetar ponteiro
            
            # Determinar MIME type
            mime_type = file.content_type or 'application/octet-stream'
            
            # Salvar no banco de dados (campos conforme o schema)
            document_data = {
                'titulo': titulo,
                'descricao': descricao,
                'categoria': categoria,
                'file_path': file_url,  # URL pública do arquivo
                'original_filename': file.filename,
                'file_size': file_size,
                'mime_type': mime_type,
                'firebase_author_uid': firebase_uid,
                'author_email': author_email,
                'downloads': 0,
                'is_public': True,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            response = supabase.table('transparency_documents').insert(document_data).execute()
            
            if response.data:
                flash('Documento enviado com sucesso!', 'success')
                return redirect(url_for('transparency.index'))
            else:
                flash('Erro ao salvar documento no banco de dados.', 'error')
                
        except Exception as e:
            print(f"Erro no upload: {e}")
            flash('Erro ao fazer upload do documento.', 'error')
    
    return render_template('admin/upload.html')

@transparency_bp.route('/download/<uuid:doc_id>')
def download(doc_id):
    """Download de documento"""
    try:
        response = supabase.table('transparency_documents').select('*').eq('id', str(doc_id)).execute()
        
        if not response.data:
            flash('Documento não encontrado.', 'error')
            return redirect(url_for('transparency.index'))
        
        document = response.data[0]
        
        # Verificar se o documento é público
        if not document.get('is_public', True):
            flash('Documento não está disponível para download.', 'error')
            return redirect(url_for('transparency.index'))
        
        # Incrementar contador de downloads
        supabase.table('transparency_documents').update({
            'downloads': document.get('downloads', 0) + 1,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }).eq('id', str(doc_id)).execute()
        
        # Redirecionar para URL do arquivo
        return redirect(document['file_path'])
        
    except Exception as e:
        print(f"Erro no download: {e}")
        flash('Erro ao baixar documento.', 'error')
        return redirect(url_for('transparency.index'))

@transparency_bp.route('/delete/<uuid:doc_id>', methods=['POST'])
@login_required
def delete(doc_id):
    """Deletar documento"""
    try:
        # Buscar documento
        response = supabase.table('transparency_documents').select('*').eq('id', str(doc_id)).execute()
        
        if not response.data:
            flash('Documento não encontrado.', 'error')
            return redirect(url_for('transparency.index'))
        
        document = response.data[0]
        
        # Verificar se o usuário tem permissão para deletar
        current_user_uid = session['user']['localId']
        if document['firebase_author_uid'] != current_user_uid:
            # Aqui você pode adicionar uma verificação de admin se necessário
            flash('Você não tem permissão para deletar este documento.', 'error')
            return redirect(url_for('transparency.index'))
        
        # Deletar do storage (opcional - pode manter para histórico)
        try:
            # Extrair o path do storage da URL
            file_url = document['file_path']
            if file_url and 'documents/' in file_url:
                # Extrair apenas o nome do arquivo da URL
                file_name = file_url.split('documents/')[-1].split('?')[0]
                supabase.storage.from_(current_app.config['BUCKET_DOCUMENTS']).remove([f"documents/{file_name}"])
        except Exception as storage_e:
            print(f"Erro ao deletar arquivo do storage: {storage_e}")
        
        # Deletar do banco
        delete_response = supabase.table('transparency_documents').delete().eq('id', str(doc_id)).execute()
        
        if delete_response.data:
            flash('Documento deletado com sucesso!', 'success')
        else:
            flash('Erro ao deletar documento.', 'error')
            
    except Exception as e:
        print(f"Erro ao deletar documento: {e}")
        flash('Erro ao deletar documento.', 'error')
    
    return redirect(url_for('transparency.index'))

@transparency_bp.route('/category/<categoria>')
def by_category(categoria):
    """Lista documentos por categoria"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    try:
        response = supabase.table('transparency_documents')\
            .select('*')\
            .eq('categoria', categoria)\
            .eq('is_public', True)\
            .order('created_at', desc=True)\
            .range(offset, offset + per_page - 1)\
            .execute()
        
        documents = response.data if response.data else []
        
        # Contar total
        count_response = supabase.table('transparency_documents')\
            .select('id', count='exact')\
            .eq('categoria', categoria)\
            .eq('is_public', True)\
            .execute()
        
        total_documents = count_response.count if count_response.count else 0
        
        has_next = total_documents > (page * per_page)
        has_prev = page > 1
        
    except Exception as e:
        print(f"Erro ao buscar documentos por categoria: {e}")
        documents = []
        has_next = False
        has_prev = False
    
    return render_template('admin/documents.html', 
                           documents=documents,
                           page=page,
                           has_next=has_next,
                           has_prev=has_prev,
                           current_category=categoria)