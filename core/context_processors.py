def roles(request):
    """
    Puts the three role flags in every template so the navigation can be built without a
    query per link.

    The flags decide what is shown, never what is allowed. Every view re-checks on the server,
    because hiding a link is not access control.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'is_customer': False, 'is_cleaner': False, 'is_administrator': False}
    return {
        'is_customer': user.is_customer,
        'is_cleaner': user.is_cleaner,
        'is_administrator': user.is_administrator,
    }
