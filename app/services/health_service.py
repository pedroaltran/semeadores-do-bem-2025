"""
Serviço de monitoramento de saúde do sistema.
"""
import logging
from datetime import datetime, timezone
from app import supabase

logger = logging.getLogger(__name__)

class HealthService:
    """Serviço para monitorar a saúde dos componentes do sistema."""
    
    @staticmethod
    def check_supabase_connection():
        """
        Verifica se a conexão com o Supabase está funcionando.
        
        Returns:
            dict: Status da conexão com detalhes
        """
        try:
            # Teste simples de conectividade
            start_time = datetime.now()
            response = supabase.table('blog_posts').select('id').limit(1).execute()
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds() * 1000  # em ms
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'message': 'Conexão com Supabase funcionando normalmente'
            }
            
        except Exception as e:
            error_str = str(e)
            
            if "521" in error_str or "Web server is down" in error_str:
                status_msg = "Servidor Supabase temporariamente indisponível"
            elif "timeout" in error_str.lower():
                status_msg = "Timeout na conexão com Supabase"
            else:
                status_msg = f"Erro na conexão com Supabase: {error_str}"
            
            logger.error(f"Erro na verificação do Supabase: {e}")
            
            return {
                'status': 'unhealthy',
                'response_time_ms': None,
                'message': status_msg,
                'error': error_str
            }
    
    @staticmethod
    def check_database_tables():
        """
        Verifica se as tabelas principais do banco estão acessíveis.
        
        Returns:
            dict: Status das tabelas
        """
        tables_to_check = ['blog_posts']
        table_status = {}
        
        for table in tables_to_check:
            try:
                response = supabase.table(table).select('id').limit(1).execute()
                table_status[table] = {
                    'status': 'accessible',
                    'message': 'Tabela acessível'
                }
            except Exception as e:
                table_status[table] = {
                    'status': 'error',
                    'message': f'Erro ao acessar tabela: {str(e)}'
                }
        
        # Determinar status geral
        all_healthy = all(t['status'] == 'accessible' for t in table_status.values())
        
        return {
            'status': 'healthy' if all_healthy else 'degraded',
            'tables': table_status
        }
    
    @staticmethod
    def get_system_health():
        """
        Retorna o status geral de saúde do sistema.
        
        Returns:
            dict: Status completo do sistema
        """
        supabase_health = HealthService.check_supabase_connection()
        database_health = HealthService.check_database_tables()
        
        # Determinar status geral do sistema
        if supabase_health['status'] == 'healthy' and database_health['status'] == 'healthy':
            overall_status = 'healthy'
        elif supabase_health['status'] == 'unhealthy':
            overall_status = 'unhealthy'
        else:
            overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {
                'supabase': supabase_health,
                'database': database_health
            },
            'uptime': HealthService._get_uptime()
        }
    
    @staticmethod
    def _get_uptime():
        """
        Calcula o tempo de atividade do sistema (simplificado).
        
        Returns:
            str: Tempo de atividade
        """
        # Em um ambiente de produção, isso seria calculado com base no tempo de início do processo
        # Por simplicidade, retornamos uma mensagem genérica
        return "Sistema em execução"
    
    @staticmethod
    def is_system_healthy():
        """
        Verifica rapidamente se o sistema está saudável.
        
        Returns:
            bool: True se o sistema estiver saudável
        """
        try:
            health = HealthService.get_system_health()
            return health['status'] in ['healthy', 'degraded']
        except Exception:
            return False