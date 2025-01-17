"""Integration between SQLAlchemy and Trino.

Some code based on
https://github.com/zzzeek/sqlalchemy/blob/rel_0_5/lib/sqlalchemy/databases/sqlite.py
which is released under the MIT license.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import re
from sqlalchemy import exc
from sqlalchemy import types
from sqlalchemy import util
# TODO shouldn't use mysql type
from sqlalchemy.databases import mysql
from sqlalchemy.engine import default
from sqlalchemy.sql import compiler
from sqlalchemy.sql.compiler import SQLCompiler

from pyhive import trino
from pyhive.common import UniversalSet
from pyhive.sqlalchemy_presto import PrestoDialect, PrestoCompiler, PrestoTypeCompiler, \
    PrestoIdentifierPreparer

class TrinoIdentifierPreparer(PrestoIdentifierPreparer):
    pass


_type_map = {
    'boolean': types.Boolean,
    'tinyint': mysql.MSTinyInteger,
    'smallint': types.SmallInteger,
    'integer': types.Integer,
    'bigint': types.BigInteger,
    'real': types.Float,
    'double': types.Float,
    'varchar': types.String,
    'timestamp': types.TIMESTAMP,
    'date': types.DATE,
    'varbinary': types.VARBINARY,
    'json': types.JSON,
}


class TrinoCompiler(PrestoCompiler):
    pass


class TrinoTypeCompiler(PrestoTypeCompiler):
    def visit_CLOB(self, type_, **kw):
        raise ValueError("Trino does not support the CLOB column type.")

    def visit_NCLOB(self, type_, **kw):
        raise ValueError("Trino does not support the NCLOB column type.")

    def visit_DATETIME(self, type_, **kw):
        return 'VARCHAR'

    def visit_FLOAT(self, type_, **kw):
        return 'DOUBLE'

    def visit_TEXT(self, type_, **kw):
        if type_.length:
            return 'VARCHAR({:d})'.format(type_.length)
        else:
            return 'VARCHAR'


class TrinoDialect(PrestoDialect):
    name = 'trino'
    type_compiler = TrinoTypeCompiler

    @classmethod
    def dbapi(cls):
        return trino

    def get_columns(self, connection, table_name, schema=None, **kw):
        rows = self._get_table_columns(connection, table_name, schema)
        result = []
        for row in rows:
            try:
                coltype = _type_map[str(row.Type).split('(')[0]]
            except KeyError:
                util.warn("Did not recognize type '%s' of column '%s'" % (row.Type, row.Column))
                coltype = types.NullType
            result.append({
                'name': row.Column,
                'type': coltype,
                # newer Presto no longer includes this column
                'nullable': getattr(row, 'Null', True),
                'default': None,
            })
        return result

    @property
    def _json_deserializer(self):
        return None
