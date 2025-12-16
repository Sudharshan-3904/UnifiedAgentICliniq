# Dev Branch

This branch of the repository acts as storagr for all our code that we worked on collaboratively

---

## Med Tool Agent

| Data    | Value                                                        |
| ------- | ------------------------------------------------------------ |
| Period  | Week 3                                                       |
| Purpose | To implement a simple prorotype of the proposed architecuter |

### Details

| Feature         | Implementation                                                                                           |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| Multiple Agents | Main Agent, Raw LLM, Safety Agent                                                                        |
| API Calls       | Fetch EHR, PubMed Search, RAG Clinical Data                                                              |
| Tools           | BMI, Target Heart Rate, Blood Volume, Daily Water Intake, Waist to hip ratio, cholestrol ldl Calculators |

---

## SiteScraper

| Paramters | Description                |
| --------- | -------------------------- |
| Input     | Links for the article      |
| Output    | One makrdown file per link |

### File structure

| Filename          | Description                                                             |
| ----------------- | ----------------------------------------------------------------------- |
| fetch_articles.py | Do the request and save them as .md files                               |
| links_to_csv.py   | Extrcat and converts the links from a .pdf file to a trackable csv file |
| url_staus.csv     | To keep track of the progress if retrieval                              |

---
