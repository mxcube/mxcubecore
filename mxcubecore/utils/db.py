import pymysql

def get_db_connection():
    connection = pymysql.connect(
        host='10.30.61.226',
        user='root',
        password='123456',
        database='data_process'
    )
    return connection

