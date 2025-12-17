import pandas as pd
import pdfx 


PDF_FILES = ["data\\Conditioned Tes - Knowledge Source - Links.pdf", "data\\Conditioned Tes - Knowledge Source - Links.pdf", "data\\Unified Tes - References - Cardiovascular System.pdf"]
CSV_FILE = "data\\url_status.csv"

def get_url_list(filename: str = ""):
    if filename:
        pdf = pdfx.PDFx(filename) 
        url_list = (pdf.get_references_as_dict())['url']
        print(f"File Read. {len(url_list)} Links Found.")
        return url_list
    else:
        return []

def create_csv(url_list: list = [], csv_filename: str = ""):
    if url_list:
        df = pd.DataFrame(columns=["id", "link", "status"])

        for i in range(len(url_list)):
            df.loc[len(df)] = [i+1, url_list[i], "yet"]
        
        print(df.shape)
        df.to_csv(csv_filename, index=False, mode="a")


create_csv(get_url_list(PDF_FILE), CSV_FILE)
