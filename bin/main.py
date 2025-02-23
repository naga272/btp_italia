from selenium.webdriver.chrome.options  import Options
from selenium.webdriver.common.by       import By
from selenium                           import webdriver
from datetime                           import datetime

import time
import pandas as pd
import sys
import os


urls     = [
    "https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/"
]



def extract_table_data_ISIN(driver, url) -> list:
    driver.get(url)
    
    # Trova tutti i div che contengono le tabelle
    table_divs = driver.find_elements(By.CLASS_NAME, "l-box")
    
    all_tables_data = []
    
    for div in table_divs:
        # Trova tutte le tabelle all'interno del div
        tables = div.find_elements(By.CLASS_NAME, "m-table")
        
        for table in tables:
            # Trova tutte le righe della tabella
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            data = {}
            
            for row in rows:
                # Trova tutte le celle (<td>) nella riga
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if len(cells) == 2:
                    key = cells[0].text.strip()
                    value = cells[1].text.strip()
                    data[key] = value
            
            # Aggiungi i dati della tabella alla lista
            if data:  # Aggiungi solo se la tabella contiene dati
                all_tables_data.append(data)
    
    return all_tables_data # lista di dict


def prendi_table(driver, url):
    
    driver.get(url)
    #driver.implicitly_wait(1)

    # Trova le tabelle
    tables = driver.find_elements(By.TAG_NAME, 'table')

    for i, table in enumerate(tables):
        rows = table.find_elements(By.TAG_NAME, 'tr')
        data = []
        for row in rows:
            # Trova tutte le celle (<td> e <th>)
            cols = row.find_elements(By.TAG_NAME, 'td') or row.find_elements(By.TAG_NAME, 'th')
            if cols:  # Se ci sono celle, estrai il testo
                cols = [col.text for col in cols]
                data.append(cols)
        
        if data:  # Se la tabella contiene dati, crea un DataFrame
            # Usa la prima riga come intestazione delle colonne
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        else:
            print("Errore: la tabella è vuota")
            return 1
            

def find_correct_btp(dfs):
    # Combina tutti i DataFrame in uno solo
    combined_df = pd.concat(dfs, ignore_index=True)

    # Sostituisci i valori vuoti con NaN e poi rimuovili
    combined_df['ULTIMO'] = combined_df['ULTIMO'].replace('', float('nan'))

    # Rimuovi le righe con valori NaN nella colonna "ULTIMO"
    combined_df = combined_df.dropna(subset=['ULTIMO'])

    # Pulisci la colonna "ULTIMO" e convertila in numeri
    combined_df['ULTIMO'] = combined_df['ULTIMO'].str.replace(',', '.').astype(float)

    # Filtra i BTP con valore inferiore a 100
    btp_corretti = combined_df[combined_df['ULTIMO'] < 100]
    return btp_corretti


def from_borsaitaliana_site(driver, url):
    '''
        borsaitaliana contiene 10 tabelle questo sito
    '''
    index = 1
    dfs = []
    while index < 9:
        print(f"lettura della pagina {index} in corso...")
        url_page = url + "lista.html?&page=" + str(index)
        df = prendi_table(driver, url_page)

        if type(df) == type(1):
            return 1

        dfs.append(df) 
        index += 1
    
    return dfs


def rendimento(df_correct, driver):

    rendimento_netto = []
    rendimento_lordo = []

    for isin in df_correct['ISIN']:
        url_page = f"{urls[0]}scheda/{str(isin)}.html"        
        print("prelevando dati da: ", url_page)

        result = extract_table_data_ISIN(driver, url_page)        
        rendimento_lordo.append(result[6]["Rendimento effettivo a scadenza lordo"])
        rendimento_netto.append(result[6]["Rendimento effettivo a scadenza netto"])

    df_correct["Rendimento effettivo a scadenza lordo"] = rendimento_lordo
    df_correct["Rendimento effettivo a scadenza netto"] = rendimento_netto

    return df_correct


def main(argc: int, argv: list) -> int:
    # Configurazione Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)

    for url in urls:
        if "borsaitaliana" in url:
            dfs = from_borsaitaliana_site(driver, url) # lista di df
            if dfs == 1:
                return 1
            else:
                df_correct = find_correct_btp(dfs)

                # https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/<isin>
                df_with_rendimento = rendimento(df_correct, driver)

                print(df_with_rendimento["Rendimento effettivo a scadenza lordo"])
                # Convert the column to numeric, coercing errors to NaN
                # i numeri sono scritti con la , al posto del .
                # i valori 0.0 sono scritti come ''
                df_with_rendimento["Rendimento effettivo a scadenza lordo"] = pd.to_numeric(
                    df_with_rendimento["Rendimento effettivo a scadenza lordo"]    
                    .str.replace(',', '.').replace('', '0.0').astype(float)       
                )

                # voglio ottenere solo i btp che hanno un rendimento superiore a 3.0
                df_with_randimento_maggiore_tre = df_with_rendimento[df_with_rendimento["Rendimento effettivo a scadenza lordo"] > 3.0]
                
                print(df_with_rendimento["Rendimento effettivo a scadenza lordo"])

                # creazione della path
                path_data = f"{datetime.now()}".replace(":", "_")
                os.mkdir(f"../flussi/borsaitaliana_{path_data}/")

                # inserisco il df nei file
                df_with_randimento_maggiore_tre.to_csv(f"../flussi/borsaitaliana_{path_data}/table.csv")
                df_with_randimento_maggiore_tre.to_html(f"../flussi/borsaitaliana_{path_data}/table.html")
                df_with_randimento_maggiore_tre.to_json(f"../flussi/borsaitaliana_{path_data}/table.json", indent=4, orient='records')

    # Chiudi il browser
    driver.quit()
    return 0


if __name__ == "__main__":
    start = time.time()
    result = main(len(sys.argv), sys.argv)
    print("tempo di esecuzione in secondi: ", time.time() - start)
    sys.exit(result)
