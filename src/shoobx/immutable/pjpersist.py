###############################################################################
#
# Copyright 2013-2019 by Shoobx, Inc.
#
###############################################################################
"""pjpersist Container of Immutables.
"""
import datetime
import persistent
import zope.interface
import zope.schema
import pjpersist.sqlbuilder as sb
from pjpersist import interfaces as pjinterfaces
from pjpersist.zope import container as pjcontainer

from shoobx.immutable import interfaces, revisioned


class NoOpProperty:

    def __get__(self, inst, cls):
        return None

    def __set__(self, inst, value):
        pass

    def __delete__(self, inst):
        pass


class Version(zope.schema.Int):
    # Unfortuantely, default Int._type is a tuple.
    _type = int


@zope.interface.implementer(pjinterfaces.IColumnSerialization)
class Immutable(revisioned.RevisionedImmutable, pjcontainer.PJContained):

    # Behave like a persistent object, but without the change notifications.
    _p_oid = None
    _p_jar = None
    _p_changed = NoOpProperty()
    _pj_name = 'name'

    # The below fields are used to auto create the SQL table names.They must
    # be in sync with `ImmutableContainer._pj_column_fields`. `id` and `data`
    # can be omitted.
    _pj_column_fields = (
        zope.schema.TextLine(__name__=_pj_name),
        Version(__name__='version'),
        zope.schema.Datetime(__name__='startOn'),
        zope.schema.Datetime(__name__='endOn'),
        zope.schema.TextLine(__name__='creator'),
        zope.schema.Text(__name__='comment'),
    )

    @property
    def __im_manager__(self):
        return self.__parent__

    def __im_is_internal_attr__(self, name):
        if name.startswith('_v_') or name.startswith('_p_'):
            return True
        if name == self._pj_name:
            return True
        return super().__im_is_internal_attr__(name)

    def __im_clone__(self):
        clone = super().__im_clone__()
        clone._p_oid = None
        return clone

    def _pj_get_column_fields(self):
        return {
            self._pj_name: getattr(self, self._pj_name),
            'version': self.__im_version__,
            'startOn': self.__im_start_on__,
            'endOn': self.__im_end_on__,
            'creator': self.__im_creator__,
            'comment': self.__im_comment__,
        }

    def __getstate__(self):
        return {
            name: value
            for name, value in self.__dict__.items()
            if (not name.startswith('_v_')
                and not name.startswith('_p_')
                and not name.startswith('_pj_'))
        }

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __repr__(self):
        return f'<{self.__class__.__name__} ({self.__name__}) at {self._p_oid}>'


class ImmutableContainer(pjcontainer.AllItemsPJContainer):

    _pj_mapping_key = 'name'

    # These fields are used to determine whether to take native SQL columns
    # instead of JSONB fields in raw_find.
    _pj_column_fields = pjcontainer.AllItemsPJContainer._pj_column_fields + (
        _pj_mapping_key, 'version', 'startOn', 'endOn', 'creator', 'comment')

    # Testing hook.
    now = datetime.datetime.now

    @property
    def _p_pj_table(self):
        return self._pj_table

    def _pj_get_resolve_filter(self):
        qry = super()._pj_get_resolve_filter()
        endOnFld = sb.Field(self._pj_table, 'endOn')
        return self._combine_filters(qry, endOnFld == None)

    def _load_one(self, id, doc, use_cache=True):
        obj = super()._load_one(id, doc, use_cache=use_cache)
        obj._p_jar.setstate(obj, doc)
        return obj

    def add(self, obj, key=None):
        res = super().add(obj, key)
        self.addRevision(obj)
        return res

    def getCurrentRevision(self, obj):
        return self[obj.__name__]

    def getRevisionHistory(self, obj):
        qry = self._combine_filters(
            super()._pj_get_resolve_filter(),
            sb.Field(self._pj_table, self._pj_mapping_key) == obj.__name__
        )
        orderBy = sb.Field(self._pj_table, 'version')
        fields = self._get_sb_fields(())
        with self._pj_jar.getCursor() as cur:
            cur.execute(
                sb.Select(fields, qry, orderBy=orderBy),
                flush_hint=[self._pj_table])
            for row in cur:
                obj = self._load_one(
                    row[self._pj_id_column], row[self._pj_data_column],
                    use_cache=False)
                yield obj

    def rollbackToRevision(self, revision, activate=False):
        cur = self._pj_jar.getCursor()
        cur.execute(sb.Delete(
            self._pj_table,
            sb.Field(self._pj_table, "version") > revision.__im_version__
        ))
        revision.__im_state__ = interfaces.IM_STATE_LOCKED
        if activate:
            revision.__im_end_on__ = None
        self._pj_jar.register(revision)
        self._cache[revision.__name__] = revision

    def addRevision(self, new, old=None):
        now = self.now()
        if old is not None:
            old.__im_end_on__ = now
            old.__im_state__ = interfaces.IM_STATE_RETIRED
            self._pj_jar.register(old)

        new.__im_start_on__ = now
        self._pj_jar.register(new)
        self._cache[new.__name__] = new
