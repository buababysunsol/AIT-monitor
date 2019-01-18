from django.contrib.auth.decorators import user_passes_test


def check_superuser(user):
    if not user.is_superuser:
        return False
    return True


def is_superuser(view_func=None, login_url=None):
    actual_decorator = user_passes_test(check_superuser, login_url=login_url)
    if view_func:
        return actual_decorator(view_func)
    return actual_decorator
