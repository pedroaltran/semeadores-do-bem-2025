"""
Serviço de cache simples para melhorar performance.
"""
import json
import time
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """Cache simples em memória com TTL (Time To Live)."""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, default_ttl: int = 300) -> Optional[Any]:
        """
        Recupera um valor do cache.
        
        Args:
            key: Chave do cache
            default_ttl: TTL padrão em segundos (5 minutos)
            
        Returns:
            Valor do cache ou None se expirado/não encontrado
        """
        if key not in self._cache:
            return None
        
        # Verificar se expirou
        if time.time() - self._timestamps[key] > default_ttl:
            self.delete(key)
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
        """
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def delete(self, key: str) -> None:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do cache
        """
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Limpa todo o cache."""
        self._cache.clear()
        self._timestamps.clear()
    
    def size(self) -> int:
        """Retorna o número de itens no cache."""
        return len(self._cache)
    
    def cleanup_expired(self, default_ttl: int = 300) -> int:
        """
        Remove itens expirados do cache.
        
        Args:
            default_ttl: TTL padrão em segundos
            
        Returns:
            Número de itens removidos
        """
        current_time = time.time()
        expired_keys = []
        
        for key, timestamp in self._timestamps.items():
            if current_time - timestamp > default_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.delete(key)
        
        return len(expired_keys)

# Instância global do cache
cache = SimpleCache()

class CacheService:
    """Serviço de cache com funcionalidades específicas para a aplicação."""
    
    @staticmethod
    def get_posts_cache_key(page: int = 1, status: str = 'published') -> str:
        """Gera chave de cache para posts."""
        return f"posts_{status}_page_{page}"
    
    @staticmethod
    def get_post_cache_key(slug: str) -> str:
        """Gera chave de cache para um post específico."""
        return f"post_{slug}"
    
    @staticmethod
    def cache_posts(posts: list, page: int = 1, status: str = 'published', ttl: int = 300) -> None:
        """
        Armazena posts no cache.
        
        Args:
            posts: Lista de posts
            page: Número da página
            status: Status dos posts
            ttl: Time to live em segundos
        """
        try:
            key = CacheService.get_posts_cache_key(page, status)
            cache_data = {
                'posts': posts,
                'cached_at': time.time(),
                'ttl': ttl
            }
            cache.set(key, cache_data)
            logger.info(f"Posts cached: {key}")
        except Exception as e:
            logger.error(f"Erro ao cachear posts: {e}")
    
    @staticmethod
    def get_cached_posts(page: int = 1, status: str = 'published', ttl: int = 300) -> Optional[list]:
        """
        Recupera posts do cache.
        
        Args:
            page: Número da página
            status: Status dos posts
            ttl: Time to live em segundos
            
        Returns:
            Lista de posts ou None se não encontrado/expirado
        """
        try:
            key = CacheService.get_posts_cache_key(page, status)
            cache_data = cache.get(key, ttl)
            
            if cache_data:
                logger.info(f"Posts retrieved from cache: {key}")
                return cache_data['posts']
            
            return None
        except Exception as e:
            logger.error(f"Erro ao recuperar posts do cache: {e}")
            return None
    
    @staticmethod
    def cache_post(post: dict, slug: str, ttl: int = 600) -> None:
        """
        Armazena um post específico no cache.
        
        Args:
            post: Dados do post
            slug: Slug do post
            ttl: Time to live em segundos (10 minutos para posts individuais)
        """
        try:
            key = CacheService.get_post_cache_key(slug)
            cache_data = {
                'post': post,
                'cached_at': time.time(),
                'ttl': ttl
            }
            cache.set(key, cache_data)
            logger.info(f"Post cached: {key}")
        except Exception as e:
            logger.error(f"Erro ao cachear post: {e}")
    
    @staticmethod
    def get_cached_post(slug: str, ttl: int = 600) -> Optional[dict]:
        """
        Recupera um post específico do cache.
        
        Args:
            slug: Slug do post
            ttl: Time to live em segundos
            
        Returns:
            Dados do post ou None se não encontrado/expirado
        """
        try:
            key = CacheService.get_post_cache_key(slug)
            cache_data = cache.get(key, ttl)
            
            if cache_data:
                logger.info(f"Post retrieved from cache: {key}")
                return cache_data['post']
            
            return None
        except Exception as e:
            logger.error(f"Erro ao recuperar post do cache: {e}")
            return None
    
    @staticmethod
    def invalidate_posts_cache() -> None:
        """Invalida o cache de posts (usado quando posts são criados/editados/deletados)."""
        try:
            # Remover todas as chaves de posts
            keys_to_remove = []
            for key in cache._cache.keys():
                if key.startswith('posts_') or key.startswith('post_'):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                cache.delete(key)
            
            logger.info(f"Cache invalidated: {len(keys_to_remove)} keys removed")
        except Exception as e:
            logger.error(f"Erro ao invalidar cache: {e}")
    
    @staticmethod
    def cleanup_cache() -> None:
        """Limpa itens expirados do cache."""
        try:
            removed = cache.cleanup_expired()
            if removed > 0:
                logger.info(f"Cache cleanup: {removed} expired items removed")
        except Exception as e:
            logger.error(f"Erro na limpeza do cache: {e}")
    
    @staticmethod
    def get_cache_stats() -> dict:
        """Retorna estatísticas do cache."""
        return {
            'size': cache.size(),
            'keys': list(cache._cache.keys())
        }