"""
Service functions for interacting with Supabase (storage, database).
"""
from flask import current_app, session
from app import supabase

def upload_file_to_supabase(file, bucket_name_param, file_path_in_bucket):
    """Upload de arquivo para o Supabase Storage usando service role."""
    try:
        # Ler o conteúdo do arquivo
        file_content = file.read()
        file.seek(0)  # Resetar o ponteiro do arquivo para o início
        
        current_app.logger.info(f"Iniciando upload para bucket: {bucket_name_param}, caminho: {file_path_in_bucket}")
        current_app.logger.info(f"Tipo de arquivo: {file.content_type}, Tamanho: {len(file_content)} bytes")
        
        # Definir o contexto do usuário para RLS (se estiver autenticado)
        if 'user' in session:
            supabase.rpc('set_firebase_user_context', {'firebase_uid': session['user']['localId']}).execute()
            current_app.logger.info(f"Contexto de usuário definido para: {session['user']['localId']}")
        
        # Upload para o Supabase Storage
        response = supabase.storage.from_(bucket_name_param).upload(
            file_path_in_bucket, 
            file_content,
            file_options={
                "content-type": file.content_type,
                "upsert": "true"  # Permite sobrescrever arquivos existentes
            }
        )
        
        current_app.logger.info(f"Upload bem-sucedido: {response}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Erro no upload: {type(e).__name__} - {str(e)}")
        if hasattr(e, 'args') and e.args:
            current_app.logger.error(f"Detalhes: {e.args}")
        raise e
