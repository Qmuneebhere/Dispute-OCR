from sqlalchemy import create_engine, text
import os

section1 = '\n\n***********************************************************\n\n'

def MarkAccounts(accList):

    # Configurations

    UID = 'CDS'
    PID = 'TIGER'
    srvr = 'unifin-sql'
    db = 'tiger'
    driver = 'ODBC+Driver+17+for+SQL+Server'

    config = f"mssql+pyodbc://{UID}:{PID}@{srvr}/{db}?driver={driver}"

    # Creating engine and connection with it

    engine = create_engine(config)

    connection = engine.raw_connection()

    # Creating cursor to execute Stored Procedure
        
    try:

        cursor = connection.cursor()
        
        print(section1)
        print('Marking Dispute Accounts in CollectOne.'.center(60))
        print(section1)

        for acc in accList:

            cursor.execute("{CALL [UFN].[Process_Dispute_Document]  (?)}", (f'{acc}',))

            print(f'{acc} marked successfully'.center(60))

        # Closing cursor and commiting changes.

        cursor.close()
        connection.commit()

        print(section1)
        print(f'{len(accList)} accounts marked successfully.'.center(60))
    
    except Exception as e: print(f'Error: {e}')

    finally:

        connection.close()

    # To close engine

    engine.dispose()


# ---------------------------------Gets Accounts List------------------------------------ #


accList = []

filePath = f'{os.getcwd()}\\DisputeAccounts.txt'

with open(filePath) as file:

    for row in file:

        unifinID = row.strip()
        accList.append(unifinID)

MarkAccounts(accList)

