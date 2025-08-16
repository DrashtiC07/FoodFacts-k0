def theme_context(request):
    """
    Add theme context to all templates
    """
    theme = request.session.get('theme', 'light')
    return {
        'current_theme': theme
    }
