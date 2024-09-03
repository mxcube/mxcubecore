#! /usr/bin/python
# -*- coding: UTF-8 -*-
import pymysql
from timeit import default_timer

host = '10.30.61.226'
port = 3306
db = 'data_process'
user = 'root'
password = '123456'


def get_connection():
    conn = pymysql.connect(host=host, port=port, db=db, user=user, password=password)
    return conn

class UsingMysql(object):

    def __init__(self, commit=True, log_time=True, log_label='总用时'):
        self._log_time = log_time
        self._commit = commit
        self._log_label = log_label

    def __enter__(self):

        if self._log_time is True:
            self._start = default_timer()

        conn = get_connection()
        # use dict cursor , different from default(tuple)
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        conn.autocommit = False

        self._conn = conn
        self._cursor = cursor
        return self

    # def __exit__(self, *exc_info):
    #     if self._commit:
    #         self._conn.commit()
    #     self._cursor.close()
    #     self._conn.close()
    #
    #     if self._log_time is True:
    #         diff = default_timer() - self._start
    #         print('-- %s: %.6f 秒' % (self._log_label, diff))

    # 添加事物提交失败后的回滚，但其实每次只提交一个sql的话是不需要的
    def __exit__(self, *exc_info):
        try:
            if exc_info[0] is not None:
                self._conn.rollback()
            elif self._commit:
                self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            print(f"Error during commit, rolled back. Exception: {e}")
            raise # 重新抛出提交事物过程中的异常
        finally:
            self._cursor.close()
            self._conn.close()

            if self._log_time is True:
                diff = default_timer() - self._start
                print('-- %s: %.6f 秒' % (self._log_label, diff))
        # 重新抛出提交事物前的异常
        if exc_info[0] is not None:
            raise exc_info[1].with_traceback(exc_info[2])
    @property
    def cursor(self):
        return self._cursor

