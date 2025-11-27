# harmony/annotations/autowired.py
def autowired_fields(**fields):
    """
    自动注入字段装饰器
    用法：
        @autowired_fields(repository="userRepo", service="userService")
        class MyClass:
            ...
    """

    def decorator(cls):
        cls.__harmony_autowired_fields__ = fields
        return cls

    return decorator
