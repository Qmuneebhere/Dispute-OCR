import pyodbc
import argparse


parser = argparse.ArgumentParser(description='Description of your script.')

parser.add_argument('user_input', type=str, help='Unifin ID: .')

args = parser.parse_args()

user_input = args.user_input

conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                      'SERVER=unifin-sql;'
                      'DATABASE=tiger;'
                      'UID=CDS;'
                      'PWD=TIGER')

cursor = conn.cursor()

unifinAccID = user_input

cursor.execute("EXEC [UFN].[Process_Dispute_Document] @dbr_no=?", unifinAccID)

conn.commit()

print(f'{unifinAccID} has been provided to stored procedure.')

cursor.close()
conn.close()