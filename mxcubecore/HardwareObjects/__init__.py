def export_method(method):
    """Decorator used to export a method programmaticly

    Args:
        method (method): The method to export
    """
    method.__exported__ = True
    return method