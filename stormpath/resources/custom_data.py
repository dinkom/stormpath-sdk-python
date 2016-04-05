"""Stormpath CustomData resource mappings."""

from dateutil.parser import parse

from .base import (
    DeleteMixin,
    Resource,
    SaveMixin,
)


class CustomData(Resource, DeleteMixin, SaveMixin):
    """CustomData Resource for custom user data.

    Resources have predefined fields that are useful to many applications,
    but you are likely to have your own custom data that you need to associate
    with a resource as well. It behaves like a Python dictionary.

    More info in documentation:
    http://docs.stormpath.com/rest/product-guide/#custom-data
    """
    data_field = 'data'
    readonly_attrs = (
        'created_at',
        'href',
        'ionmeta',
        'ion_meta',
        'meta',
        'modified_at',
        'spmeta',
        'sp_meta',
        'sp_http_status',
    )

    exposed_readonly_timestamp_attrs = (
        'created_at',
        'modified_at',
    )

    def __init__(self, *args, **kwargs):
        super(CustomData, self).__init__(*args, **kwargs)
        self._deletes = set([])

    def __getitem__(self, key):
        if (key not in self.data) and (self._get_key_href(key) not in self._deletes):
            self._ensure_data()

        return getattr(self, self.data_field)[key]

    def __setitem__(self, key, value):
        if key in self.readonly_attrs or \
                self.from_camel_case(key) in self.readonly_attrs:
            raise KeyError(
                "Custom data property '%s' is not writable" % (key))
        else:
            if key.startswith('-'):
                raise KeyError(
                    "Usage of '-' at the beginning of key is not allowed")

            key_href = self._get_key_href(key)
            if key_href in self._deletes:
                self._deletes.remove(key_href)

            getattr(self, self.data_field)[key] = value

    def __delitem__(self, key):
        if key in self.exposed_readonly_timestamp_attrs:
            raise KeyError(
                "Custom data property '%s' is not deletable" % (key))

        self._ensure_data()

        for href in self._deletes:
            try:
                del self.data[href.split('/')[-1]]
            except KeyError:
                pass

        del self.data[key]

        if not self.is_new():
            self._deletes.add(self._get_key_href(key))

    def __contains__(self, key):
        self._ensure_data()
        return key in self.data

    def __setattr__(self, name, value):
        ctype = self.get_resource_attributes().get(name)

        if ctype and not isinstance(value, ctype) \
                and name in self.writable_attrs:
            getattr(self, name)._set_properties(value)
        elif name.startswith('_') or name in self.writable_attrs:
            super(Resource, self).__setattr__(name, value)
        else:
            raise AttributeError("Attribute '%s' of %s is not writable" %
                (name, self.__class__.__name__))

    def __getattr__(self, name):
        if name == 'href':
            return self.__dict__.get('href')

        self._ensure_data()

        if name in self.__dict__:
            return self.__dict__[name]
        elif name in self.__dict__[self.data_field]:
            return self.__dict__[self.data_field][name]
        else:
            raise AttributeError(
                "%s has no attribute '%s'" %
                (self.__class__.__name__, name))

    def _get_key_href(self, key):
        return '%s/%s' % (self.href, key)

    def keys(self):
        self._ensure_data()
        return self.data.keys()

    def values(self):
        self._ensure_data()
        return self.data.values()

    def items(self):
        self._ensure_data()
        return self.data.items()

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __iter__(self):
        self._ensure_data()
        return iter(self.data)

    def _get_properties(self):
        writable_attrs = set(self.data) - set(
            self.exposed_readonly_timestamp_attrs)
        return {k: self.data[k] for k in writable_attrs}

    def _set_properties(self, properties, overwrite=False):
        self.__dict__[self.data_field] = self.__dict__.get(self.data_field, {})
        for k, v in properties.items():
            kcc = self.from_camel_case(k)
            if kcc in self.readonly_attrs:
                if kcc in self.exposed_readonly_timestamp_attrs:
                    v = parse(v)
                    self.__dict__[self.data_field][kcc] = v
                self.__dict__[kcc] = v
            else:
                if k not in self.__dict__[self.data_field]:
                    self.__dict__[self.data_field][k] = v

    def save(self):
        for href in self._deletes:
            self._store.delete_resource(href)

        self._deletes = set()

        if self.data_field in self.__dict__ and len(self._get_properties()):
            super(CustomData, self).save()

    def delete(self):
        super(CustomData, self).delete()
        self.__dict__[self.data_field] = {}
