"""
Blog-related routes (listing, viewing, creating, editing, deleting posts).
"""
import re
import unicodedata
import logging
import math
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from app import supabase
from app.utils.decorators import login_required
from app.services.file_service import allowed_file, generate_unique_filename
from app.services.supabase_service import upload_file_to_supabase
from app.services.health_service import HealthService
from app.services.cache_service import CacheService

blog_bp = Blueprint('blog', __name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_supabase_available():
    """Verifica se o Supabase está disponível"""
    return HealthService.is_system_healthy()

def handle_supabase_error(error, operation="operação"):
    """Trata erros do Supabase de forma consistente"""
    error_str = str(error)
    
    if "521" in error_str or "Web server is down" in error_str:
        message = f"Serviço temporariamente indisponível. Tente novamente em alguns minutos."
        logger.error(f"Erro 521 do Supabase durante {operation}: {error}")
    elif "timeout" in error_str.lower():
        message = f"Tempo limite excedido. Tente novamente."
        logger.error(f"Timeout do Supabase durante {operation}: {error}")
    else:
        message = f"Erro interno do servidor. Tente novamente mais tarde."
        logger.error(f"Erro do Supabase durante {operation}: {error}")
    
    return message

def generate_slug(title):
    """Gera um slug amigável a partir do título"""
    # Normalizar caracteres unicode
    slug = unicodedata.normalize('NFKD', title)
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    
    # Converter para minúsculas e substituir espaços por hífens
    slug = slug.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')
    
    return slug

@blog_bp.route('/')
def index():
    """Lista todos os posts do blog com paginação"""
    page = request.args.get('page', 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page

    is_authenticated = 'user' in session

    # Tentar recuperar do cache primeiro
    cached_posts = CacheService.get_cached_posts(page, 'published')
    if cached_posts is not None:
        logger.info("Posts recuperados do cache")
        has_next = len(cached_posts) == per_page
        has_prev = page > 1
        # Suponha que você não tenha total_pages no cache
        total_pages = page + 1 if has_next else page

        return render_template('blog.html',
                               posts=cached_posts,
                               page=page,
                               total_pages=total_pages,
                               has_next=has_next,
                               has_prev=has_prev,
                               is_authenticated=is_authenticated)

    try:
        if not is_supabase_available():
            flash('Serviço temporariamente indisponível. Tente novamente em alguns minutos.', 'error')
            return render_template('blog.html',
                                   posts=[],
                                   page=1,
                                   total_pages=1,
                                   has_next=False,
                                   has_prev=False,
                                   is_authenticated=False), 503

        posts = []
        total_posts = 0
        total_pages = 1
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = supabase.table('blog_posts') \
                    .select('*') \
                    .eq('status', 'published') \
                    .order('created_at', desc=True) \
                    .range(offset, offset + per_page - 1) \
                    .execute()

                posts = response.data if response.data else []

                for post in posts:
                    if 'created_at' in post and post['created_at']:
                        try:
                            post['created_at'] = datetime.fromisoformat(post['created_at']).strftime('%d/%m/%Y')
                        except Exception as e:
                            logger.warning(f"Erro ao formatar data: {e}")

                count_response = supabase.table('blog_posts') \
                    .select('id', count='exact') \
                    .eq('status', 'published') \
                    .execute()

                total_posts = count_response.count or (offset + len(posts))
                total_pages = math.ceil(total_posts / per_page)

                if posts:
                    CacheService.cache_posts(posts, page, 'published')

                break
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou ao buscar posts: {e}")
                if attempt == max_retries - 1:
                    error_msg = handle_supabase_error(e, "busca de posts")
                    flash(error_msg, 'error')
                    posts = []
                    total_posts = 0
                    total_pages = 1

        has_next = total_posts > (page * per_page)
        has_prev = page > 1

    except Exception as e:
        error_msg = handle_supabase_error(e, "busca de posts")
        flash(error_msg, 'error')
        posts = []
        has_next = False
        has_prev = False
        total_pages = 1

    return render_template('blog.html',
                           posts=posts,
                           page=page,
                           total_pages=total_pages,
                           has_next=has_next,
                           has_prev=has_prev,
                           is_authenticated=is_authenticated)


@blog_bp.route('/view/<uuid:post_id>')
def view_post_by_id(post_id):
    """Exibe um post específico por ID (UUID)"""
    post_id_str = str(post_id)
    logger.info(f"Attempting to view post with ID: {post_id_str}")

    try:
        # Verificar disponibilidade do Supabase
        if not is_supabase_available():
            logger.warning("Supabase not available")
            flash('Serviço temporariamente indisponível. Tente novamente em alguns minutos.', 'error')
            return redirect(url_for('blog.index'))

        # Buscar post por ID com retry
        max_retries = 3
        post = None

        for attempt in range(max_retries):
            try:
                response = supabase.table('blog_posts').select('*').eq('id', post_id_str).single().execute()
                logger.info(f"Supabase response data type: {type(response.data)}")

                if not response.data:
                    logger.warning(f"Post not found: {post_id_str}")
                    flash('Post não encontrado.', 'error')
                    return redirect(url_for('blog.index'))

                post = response.data
                logger.info(f"Post found: {post.get('title', 'No title')}")
                break

            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    error_msg = handle_supabase_error(e, "busca de post por ID")
                    flash(error_msg, 'error')
                    return redirect(url_for('blog.index'))
                logger.warning(f"Tentativa {attempt + 1} falhou ao buscar post por ID: {e}")

        # Verificar se o post está publicado (opcional)
        if post.get('status') != 'published':
            if 'user' not in session:
                flash('Post não encontrado.', 'error')
                return redirect(url_for('blog.index'))

        # Incrementar visualizações (não crítico se falhar)
        try:
            views = post.get('views', 0) + 1
            supabase.table('blog_posts').update({'views': views}).eq('id', post_id_str).execute()
            post['views'] = views
        except Exception as e:
            logger.warning(f"Erro ao incrementar visualizações: {e}")

        # Formatando as datas no padrão dd/mm/yyyy
        try:
            if post.get('created_at'):
                post['created_at'] = datetime.fromisoformat(post['created_at']).strftime('%d/%m/%Y')
            if post.get('updated_at'):
                post['updated_at'] = datetime.fromisoformat(post['updated_at']).strftime('%d/%m/%Y')
        except Exception as e:
            logger.warning(f"Erro ao formatar datas: {e}")

        is_authenticated = 'user' in session
        return render_template('post.html', post=post, is_authenticated=is_authenticated)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        error_msg = handle_supabase_error(e, "busca de post por ID")
        flash(error_msg, 'error')
        return redirect(url_for('blog.index'))


@blog_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """Criar novo post"""
    if request.method == 'POST':
        try:
            # Verificar disponibilidade do Supabase
            if not is_supabase_available():
                error_msg = "Serviço temporariamente indisponível. Tente novamente em alguns minutos."
                flash(error_msg, 'error')
                return render_template('admin/new_post.html'), 503
            
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            excerpt = request.form.get('excerpt', '').strip()
            status = request.form.get('status', 'draft')
            tags = request.form.get('tags', '').strip()
            meta_description = request.form.get('meta_description', '').strip()
            featured = request.form.get('featured') == 'on'
            
            # Validação básica
            if not title or len(title) < 5:
                flash('O título deve ter pelo menos 5 caracteres.', 'error')
                return render_template('admin/new_post.html')
            
            if not content or len(content) < 10:
                flash('O conteúdo deve ter pelo menos 10 caracteres.', 'error')
                return render_template('admin/new_post.html')
            
            # Gerar slug único
            base_slug = generate_slug(title)
            slug = base_slug
            counter = 1
            
            # Verificar se o slug já existe (com retry)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    existing = supabase.table('blog_posts').select('id').eq('slug', slug).execute()
                    if not existing.data:
                        break
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    logger.warning(f"Tentativa {attempt + 1} falhou ao verificar slug: {e}")
            
            # Upload de imagem se fornecida
            image_url = None
            if 'image' in request.files and request.files['image'].filename:
                file = request.files['image']
                if allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS_IMG']):
                    try:
                        filename = generate_unique_filename(file.filename)
                        file_path = f"blog/{filename}"
                        
                        upload_file_to_supabase(file, current_app.config['BUCKET_BLOG_IMAGES'], file_path)
                        image_url = supabase.storage.from_(current_app.config['BUCKET_BLOG_IMAGES']).get_public_url(file_path)
                    except Exception as e:
                        logger.error(f"Erro no upload da imagem: {e}")
                        flash('Erro ao fazer upload da imagem. Post será criado sem imagem.', 'warning')
            
            # Criar post
            post_data = {
                'title': title,
                'slug': slug,
                'content': content,
                'excerpt': excerpt,
                'status': status,
                'image_url': image_url,
                'tags': tags,
                'meta_description': meta_description,
                'firebase_author_uid': session['user']['localId'],
                'author_email': session['user']['email'],
                'created_at': datetime.now(timezone.utc).isoformat(),
                'views': 0,
                'featured': featured
            }
            
            # Tentar inserir com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = supabase.table('blog_posts').insert(post_data).execute()
                    
                    if response.data:
                        # Invalidar cache após criação bem-sucedida
                        CacheService.invalidate_posts_cache()
                        
                        # Verificar se é requisição AJAX
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                            return jsonify({'success': True, 'message': 'Post criado com sucesso!'}), 200
                        
                        flash('Post criado com sucesso!', 'success')
                        return redirect(url_for('admin.dashboard'))
                    else:
                        # Verificar se é requisição AJAX
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                            return jsonify({'success': False, 'message': 'Erro ao criar post. Dados não foram salvos.'}), 400
                        
                        flash('Erro ao criar post. Dados não foram salvos.', 'error')
                        return render_template('admin/new_post.html')
                        
                except Exception as e:
                    if attempt == max_retries - 1:
                        error_msg = handle_supabase_error(e, "criação de post")
                        flash(error_msg, 'error')
                        return render_template('admin/new_post.html'), 503
                    logger.warning(f"Tentativa {attempt + 1} falhou ao criar post: {e}")
                
        except Exception as e:
            error_msg = handle_supabase_error(e, "criação de post")
            flash(error_msg, 'error')
            return render_template('admin/new_post.html'), 500
    
    return render_template('admin/new_post.html')

@blog_bp.route('/edit/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Editar post existente"""
    try:
        # Verificar disponibilidade do Supabase
        if not is_supabase_available():
            flash('Serviço temporariamente indisponível. Tente novamente em alguns minutos.', 'error')
            return redirect(url_for('admin.posts'))
        
        # Buscar post com retry
        max_retries = 3
        post = None
        
        for attempt in range(max_retries):
            try:
                response = supabase.table('blog_posts').select('*').eq('id', post_id).execute()
                
                if not response.data:
                    flash('Post não encontrado.', 'error')
                    return redirect(url_for('admin.posts'))
                
                post = response.data[0]
                break
                
            except Exception as e:
                if attempt == max_retries - 1:
                    error_msg = handle_supabase_error(e, "busca de post para edição")
                    flash(error_msg, 'error')
                    return redirect(url_for('admin.posts'))
                logger.warning(f"Tentativa {attempt + 1} falhou ao buscar post para edição: {e}")
        
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form.get('content', '').strip()
            excerpt = request.form.get('excerpt', '').strip()
            status = request.form.get('status', 'draft')
            tags = request.form.get('tags', '').strip()
            meta_description = request.form.get('meta_description', '').strip()
            featured = request.form.get('featured') == 'on'
            
            # Validação básica
            if not title or len(title) < 5:
                flash('O título deve ter pelo menos 5 caracteres.', 'error')
                return render_template('admin/edit_post.html', post=post)
            
            if not content or len(content) < 10:
                flash('O conteúdo deve ter pelo menos 10 caracteres.', 'error')
                return render_template('admin/edit_post.html', post=post)
            
            # Atualizar slug se título mudou
            slug = post['slug']
            if title != post['title']:
                new_slug = generate_slug(title)
                
                # Verificar se novo slug já existe
                try:
                    existing = supabase.table('blog_posts').select('id').eq('slug', new_slug).neq('id', post_id).execute()
                    if not existing.data:
                        slug = new_slug
                except Exception as e:
                    logger.warning(f"Erro ao verificar slug único: {e}")
            
            # Upload de nova imagem se fornecida
            image_url = post.get('image_url')
            if 'image' in request.files and request.files['image'].filename:
                file = request.files['image']
                if allowed_file(file.filename, current_app.config['ALLOWED_EXTENSIONS_IMG']):
                    try:
                        filename = generate_unique_filename(file.filename)
                        file_path = f"blog/{filename}"
                        
                        upload_file_to_supabase(file, current_app.config['BUCKET_BLOG_IMAGES'], file_path)
                        image_url = supabase.storage.from_(current_app.config['BUCKET_BLOG_IMAGES']).get_public_url(file_path)
                    except Exception as e:
                        logger.error(f"Erro no upload da imagem: {e}")
                        flash('Erro ao fazer upload da imagem. Post será atualizado sem alterar a imagem.', 'warning')
            
            # Atualizar post
            update_data = {
                'title': title,
                'slug': slug,
                'content': content,
                'excerpt': excerpt,
                'status': status,
                'image_url': image_url,
                'tags': tags,
                'meta_description': meta_description,
                'featured': featured,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Tentar atualizar com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    update_response = supabase.table('blog_posts').update(update_data).eq('id', post_id).execute()
                    
                    if update_response.data:
                        # Invalidar cache após atualização bem-sucedida
                        CacheService.invalidate_posts_cache()
                        
                        # Verificar se é requisição AJAX
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                            return jsonify({'success': True, 'message': 'Post atualizado com sucesso!'}), 200
                        
                        flash('Post atualizado com sucesso!', 'success')
                        return redirect(url_for('admin.dashboard'))
                    else:
                        # Verificar se é requisição AJAX
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
                            return jsonify({'success': False, 'message': 'Erro ao atualizar post. Dados não foram salvos.'}), 400
                        
                        flash('Erro ao atualizar post. Dados não foram salvos.', 'error')
                        return render_template('admin/edit_post.html', post=post)
                        
                except Exception as e:
                    if attempt == max_retries - 1:
                        error_msg = handle_supabase_error(e, "atualização de post")
                        flash(error_msg, 'error')
                        return render_template('admin/edit_post.html', post=post)
                    logger.warning(f"Tentativa {attempt + 1} falhou ao atualizar post: {e}")
        
        return render_template('admin/edit_post.html', post=post)
        
    except Exception as e:
        error_msg = handle_supabase_error(e, "edição de post")
        flash(error_msg, 'error')
        return redirect(url_for('admin.posts'))

@blog_bp.route('/posts')
@login_required
def posts():
    """Lista todos os posts do blog para administração com paginação"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10  # Posts por página
        offset = (page - 1) * per_page
        
        # Verificar disponibilidade do Supabase
        if not is_supabase_available():
            flash('Serviço temporariamente indisponível. Tente novamente em alguns minutos.', 'error')
            return render_template('admin/posts.html', 
                                 posts=[], 
                                 page=1,
                                 has_next=False,
                                 has_prev=False), 503
        
        # Buscar todos os posts (publicados e rascunhos) com retry
        max_retries = 3
        posts = []
        total_posts = 0
        
        for attempt in range(max_retries):
            try:
                # Buscar posts com paginação
                response = supabase.table('blog_posts').select('*').order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
                posts = response.data if response.data else []
                
                # Contar total de posts para paginação
                count_response = supabase.table('blog_posts').select('id', count='exact').execute()
                total_posts = count_response.count if count_response.count else 0
                
                break
                
            except Exception as e:
                if attempt == max_retries - 1:
                    error_msg = handle_supabase_error(e, "busca de posts para administração")
                    flash(error_msg, 'error')
                    posts = []
                    total_posts = 0
                logger.warning(f"Tentativa {attempt + 1} falhou ao buscar posts: {e}")
        
        # Calcular paginação
        has_next = total_posts > (page * per_page)
        has_prev = page > 1
        
        return render_template('admin/posts.html',
                             posts=posts,
                             page=page,
                             has_next=has_next,
                             has_prev=has_prev)
        
    except Exception as e:
        error_msg = handle_supabase_error(e, "carregamento de posts para administração")
        flash(error_msg, 'error')
        return redirect(url_for('admin.dashboard'))
    
@blog_bp.route('/delete/<post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    """Deletar post"""
    try:
        # Verificar disponibilidade do Supabase
        if not is_supabase_available():
            flash('Serviço temporariamente indisponível. Tente novamente em alguns minutos.', 'error')
            return redirect(url_for('blog.posts'))
        
        # Tentar deletar com retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = supabase.table('blog_posts').delete().eq('id', post_id).execute()
                
                if response.data:
                    # Invalidar cache após exclusão bem-sucedida
                    CacheService.invalidate_posts_cache()
                    flash('Post deletado com sucesso!', 'success')
                else:
                    flash('Erro ao deletar post. Post não encontrado.', 'error')
                break
                
            except Exception as e:
                if attempt == max_retries - 1:
                    error_msg = handle_supabase_error(e, "exclusão de post")
                    flash(error_msg, 'error')
                logger.warning(f"Tentativa {attempt + 1} falhou ao deletar post: {e}")
            
    except Exception as e:
        error_msg = handle_supabase_error(e, "exclusão de post")
        flash(error_msg, 'error')
    
    return redirect(url_for('blog.posts'))

# Rota para limpeza de cache (apenas para administradores)
@blog_bp.route('/cache/cleanup', methods=['POST'])
@login_required
def cleanup_cache():
    """Endpoint para limpeza manual do cache"""
    try:
        CacheService.cleanup_cache()
        stats = CacheService.get_cache_stats()
        
        return jsonify({
            'status': 'success',
            'message': 'Cache limpo com sucesso',
            'cache_stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na limpeza do cache: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Rota para invalidar todo o cache (apenas para administradores)
@blog_bp.route('/cache/invalidate', methods=['POST'])
@login_required
def invalidate_cache():
    """Endpoint para invalidação manual do cache"""
    try:
        CacheService.invalidate_posts_cache()
        stats = CacheService.get_cache_stats()
        
        return jsonify({
            'status': 'success',
            'message': 'Cache invalidado com sucesso',
            'cache_stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Erro na invalidação do cache: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Rotas para tags e categorias
@blog_bp.route('/tags')
def list_tags():
    """Lista todas as tags disponíveis"""
    try:
        if not is_supabase_available():
            return jsonify({'error': 'Serviço indisponível'}), 503
        
        response = supabase.table('tags').select('*').order('name').execute()
        tags = response.data if response.data else []
        
        return jsonify({'tags': tags})
        
    except Exception as e:
        logger.error(f"Erro ao buscar tags: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@blog_bp.route('/categories')
def list_categories():
    """Lista todas as categorias disponíveis"""
    try:
        if not is_supabase_available():
            return jsonify({'error': 'Serviço indisponível'}), 503
        
        response = supabase.table('categories').select('*').order('name').execute()
        categories = response.data if response.data else []
        
        return jsonify({'categories': categories})
        
    except Exception as e:
        logger.error(f"Erro ao buscar categorias: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@blog_bp.route('/featured')
def featured_posts():
    """Lista posts em destaque"""
    try:
        if not is_supabase_available():
            flash('Serviço temporariamente indisponível.', 'error')
            return render_template('blog.html', posts=[], page=1, has_next=False, has_prev=False, is_authenticated=False), 503
        
        response = supabase.table('blog_posts').select('*').eq('status', 'published').eq('featured', True).order('created_at', desc=True).limit(6).execute()
        posts = response.data if response.data else []
        
        is_authenticated = 'user' in session
        
        return render_template('blog.html', 
                             posts=posts, 
                             page=1,
                             has_next=False,
                             has_prev=False,
                             is_authenticated=is_authenticated,
                             featured_only=True)
        
    except Exception as e:
        error_msg = handle_supabase_error(e, "busca de posts em destaque")
        flash(error_msg, 'error')
        return render_template('blog.html', posts=[], page=1, has_next=False, has_prev=False, is_authenticated=False)

@blog_bp.route('/search')
def search_posts():
    """Busca posts por termo"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 6
    offset = (page - 1) * per_page
    
    if not query:
        flash('Digite um termo para buscar.', 'warning')
        return redirect(url_for('blog.index'))
    
    try:
        if not is_supabase_available():
            flash('Serviço temporariamente indisponível.', 'error')
            return render_template('blog.html', posts=[], page=1, has_next=False, has_prev=False, is_authenticated=False), 503
        
        # Buscar posts que contenham o termo no título ou conteúdo
        response = supabase.table('blog_posts').select('*').eq('status', 'published').or_(f'title.ilike.%{query}%,content.ilike.%{query}%,tags.ilike.%{query}%').order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        posts = response.data if response.data else []
        
        # Contar total para paginação
        count_response = supabase.table('blog_posts').select('id', count='exact').eq('status', 'published').or_(f'title.ilike.%{query}%,content.ilike.%{query}%,tags.ilike.%{query}%').execute()
        total_posts = count_response.count if count_response.count else 0
        
        has_next = total_posts > (page * per_page)
        has_prev = page > 1
        is_authenticated = 'user' in session
        
        return render_template('blog.html', 
                             posts=posts, 
                             page=page,
                             has_next=has_next,
                             has_prev=has_prev,
                             is_authenticated=is_authenticated,
                             search_query=query)
        
    except Exception as e:
        error_msg = handle_supabase_error(e, "busca de posts")
        flash(error_msg, 'error')
        return render_template('blog.html', posts=[], page=1, has_next=False, has_prev=False, is_authenticated=False)