"""
Core translation module that provides the main trans function.
This module serves as the primary interface for translations across the application.
"""

from .general_tools.general_translations import GENERAL_TRANSLATIONS
from flask import session, has_request_context, g
import logging

# Set up logger
logger = logging.getLogger('ficore_app.translations.core')

def trans(key, lang=None, **kwargs):
    """
    Main translation function that serves as the primary interface.
    
    Args:
        key: Translation key
        lang: Language code ('en', 'ha'). Defaults to session['lang'] or 'en'
        **kwargs: String formatting parameters
    
    Returns:
        Translated string with formatting applied
    """
    # Import the main trans function from __init__.py to avoid circular imports
    from . import trans as main_trans
    return main_trans(key, lang=lang, **kwargs)

def get_translations(lang=None):
    """
    Get all general translations for a language.
    
    Args:
        lang: Language code ('en', 'ha'). Defaults to session['lang'] or 'en'
    
    Returns:
        Dictionary of general translations
    """
    if lang is None:
        lang = session.get('lang', 'en') if has_request_context() else 'en'
    
    return GENERAL_TRANSLATIONS.get(lang, GENERAL_TRANSLATIONS.get('en', {}))

# Export the main trans function for backward compatibility
__all__ = ['trans', 'get_translations']