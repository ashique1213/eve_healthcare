import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY_CENTRES_LIST = 'centres_list_cache'
CACHE_KEY_TESTS_LIST = 'tests_list_cache'
CACHE_TIMEOUT = 300  # 5 minutes


def invalidate_centres_cache():
    """Invalidates cached diagnostic centres data."""
    try:
        cache.delete(CACHE_KEY_CENTRES_LIST)
        logger.info("Centres cache invalidated successfully.")
    except Exception as e:
        logger.warning(f"Failed to invalidate centres cache: {e}")


def invalidate_tests_cache():
    """Invalidates cached diagnostic tests data."""
    try:
        cache.delete(CACHE_KEY_TESTS_LIST)
        logger.info("Tests cache invalidated successfully.")
    except Exception as e:
        logger.warning(f"Failed to invalidate tests cache: {e}")
