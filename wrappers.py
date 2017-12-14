# -*- coding: utf-8 -*-


def db_auto_update_modification_time(cls):
    """
    Декоратор предназначенный для автоматического изменения полей created и modified во время вызова метода save.
    Объявление выше указанных полей обязательно в модели.
    :param cls:
    :return:
    """
    if hasattr(cls, 'save'):
        import datetime

        def update_create_modify(func):
            def wrap_update_created_modified_fields(self, *args, **params):
                update_time = datetime.datetime.utcnow()
                if not getattr(self, 'created', None):
                    setattr(self, 'created', update_time)
                setattr(self, 'modified', update_time)
                return func(self, *args, **params)

            return wrap_update_created_modified_fields

        cls.save = update_create_modify(cls.save)

    return cls
