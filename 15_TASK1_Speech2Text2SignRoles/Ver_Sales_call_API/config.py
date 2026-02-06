import os

basedir = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/sales_calls'
SQLALCHEMY_TRACK_MODIFICATIONS = False