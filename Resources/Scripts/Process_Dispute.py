import pyodbc

conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                      'SERVER=unifin-sql;'
                      'DATABASE=tiger;'
                      'UID=CDS;'
                      'PWD=TIGER')

cursor = conn.cursor()

unifinAccID = '0000000008'

cursor.execute("EXEC [UFN].[Process_Dispute_Document] @dbr_no=?", unifinAccID)

conn.commit()

cursor.close()
conn.close()