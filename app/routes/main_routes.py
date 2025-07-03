"""
Main application routes (e.g., home page, contact form API).
"""
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, session, abort
from app import supabase

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    is_authenticated = 'user' in session
    
    try:
        # Buscar posts publicados
        posts_response = supabase.table('blog_posts').select('*').eq('status', 'published').order('created_at', desc=True).limit(6).execute()
        posts = posts_response.data if posts_response.data else []
        
        # Buscar documentos de transparência
        docs_response = supabase.table('transparency_documents').select('*').order('created_at', desc=True).limit(10).execute()
        documentos = docs_response.data if docs_response.data else []

        # Converte created_at para datetime
        for doc in documentos:
            try:
                doc['created_at'] = datetime.fromisoformat(doc['created_at'].replace('Z', ''))
            except:
                pass

        for post in posts:
            try:
                post['created_at'] = datetime.fromisoformat(post['created_at'].replace('Z', ''))
            except:
                pass
        
    except Exception as e:
        print(f"Erro ao buscar dados: {e}")
        posts = []
        documentos = []
    
    return render_template('index.html', 
                           is_authenticated=is_authenticated,
                           posts=posts,
                           documentos=documentos)

@main_bp.route('/api/enviar-email', methods=['POST'])
def enviar_email():
    try:
        print("==== START FORM DEBUG ====")
        print(f"Form data received: {request.form}")
        print(f"Form data keys: {list(request.form.keys())}")
        
        # Obter dados do formulário
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        
        # Usando consistentemente o campo com underscore
        tipo_contribuicao = request.form.get('tipo_contribuicao')
        
        mensagem = request.form.get('mensagem', '')
        
        print(f"Parsed data:")
        print(f"- nome: {nome}")
        print(f"- telefone: {telefone}")
        print(f"- email: {email}")
        print(f"- tipo_contribuicao: {tipo_contribuicao}")
        print("==== END FORM DEBUG ====")
        
        # Validação de campos obrigatórios
        if not nome or not telefone or not email or not tipo_contribuicao:
            missing = []
            if not nome: missing.append("nome")
            if not telefone: missing.append("telefone")
            if not email: missing.append("email") 
            if not tipo_contribuicao: missing.append("tipo de contribuição")
            
            print(f"Missing required fields: {missing}")
            return jsonify({
                'success': False, 
                'message': f'Os seguintes campos obrigatórios devem ser preenchidos: {", ".join(missing)}'
            }), 400
        
        # Validação simples de e-mail
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False, 
                'message': 'Por favor, informe um e-mail válido'
            }), 400
            
        # Preparar dados para salvar no banco
        mensagem_data = {
            'nome': nome,
            'telefone': telefone,
            'email': email,
            'tipo_contribuicao': tipo_contribuicao, # Mantido igual no banco
            'mensagem': mensagem,
            'status': 'nova',
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Inserir no banco de dados
        response = supabase.table('contact_messages').insert(mensagem_data).execute()
        
        if not response.data:
            raise Exception("Nenhum dado retornado após a inserção")
            
        return jsonify({
            'success': True, 
            'message': 'Mensagem enviada com sucesso! Entraremos em contato em breve.'
        })
        
    except Exception as e:
        print(f"Erro ao salvar mensagem: {e}")
        error_message = str(e)
        
        # Tentar extrair mensagem de erro mais útil se for do Supabase
        if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict):
            error_details = e.args[0]
            error_message = error_details.get('message', str(e))
            
        return jsonify({
            'success': False, 
            'message': f'Erro ao processar mensagem: {error_message}'
        }), 500
