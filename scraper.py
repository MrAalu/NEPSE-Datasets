import os, time, random, requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta


class NepseStockScraper:
    def __init__(self, output_file="NEPSE_STOCKS_DATASETS.csv", start_date=None):
        self.url = "https://www.sharesansar.com/today-share-price"
        self.api_url = "https://www.sharesansar.com/ajaxtodayshareprice"
        self.output_file = output_file
        self.start_date = start_date
        self.end_date = datetime.today().strftime("%Y-%m-%d")

    def get_csrf_token(self, session):
        response = session.get(self.url)
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "_token"}).get("value")
        return token

    def get_html(self, session, date, token):
        payload = {"_token": token, "sector": "all_sec", "date": date}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
        }
        response = session.post(self.api_url, data=payload, headers=headers)
        return response.text, date

    def parse_html(self, html, date):
        soup = BeautifulSoup(html, "html.parser")
        h5_tag = soup.find("h5")

        if not h5_tag or "As of :" not in h5_tag.text:
            print(f"No valid h5 tag found for date: {date}")
            return []

        date_span = h5_tag.find("span", class_="text-org")
        stock_date = date_span.text.strip() if date_span else date

        table = soup.find("table", id="headFixed")
        if not table:
            print(f"No table found for date: {date}")
            return []

        tbody = table.find("tbody")
        rows = tbody.find_all("tr") if tbody else []
        if not rows or "No Record Found." in rows[0].text:
            print(f"No records found for date: {date}")
            return []

        data = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 9:
                continue

            # s_no = cells[0].text.strip()
            symbol = cells[1].text.strip()
            open_price = cells[3].text.strip()
            high_price = cells[4].text.strip()
            low_price = cells[5].text.strip()
            close_price = cells[6].text.strip()
            volume = cells[8].text.strip()
            data.append(
                [
                    # s_no,
                    symbol,
                    stock_date,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                ]
            )
        return data

    def generate_dates(self, start_date, end_date):
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        delta = timedelta(days=1)
        current = start
        while current <= end:
            yield current.strftime("%Y-%m-%d")
            current += delta

    def setup_dates(self):
        if os.path.exists(self.output_file):
            df_existing = pd.read_csv(self.output_file)
            max_date = pd.to_datetime(df_existing["Date"]).max()
            self.start_date = (max_date + timedelta(days=1)).strftime("%Y-%m-%d")

    def format_datasets(self):
        """
        preprocessiing the raw/scraped .csv dataset into a standard format
        """
        # reading the CSV file with specified data types for numeric columns
        data = pd.read_csv(
            self.output_file,
            dtype={"Open": str, "High": str, "Low": str, "Close": str, "Vol": str},
            low_memory=False,
        )

        # revmoning '.csv' from the Date col and also converting to datetime
        data["Date"] = pd.to_datetime(
            data["Date"].str.replace(".csv", "", regex=False), errors="coerce"
        )

        def clean_numeric(column):
            return pd.to_numeric(
                column.str.replace(",", "", regex=False), errors="coerce"
            )

        def clean_numeric_volume(column):
            return pd.to_numeric(
                column.str.replace(",", "", regex=False), errors="coerce"
            ).astype(int)

        data["Open"] = clean_numeric(data["Open"])
        data["High"] = clean_numeric(data["High"])
        data["Low"] = clean_numeric(data["Low"])
        data["Close"] = clean_numeric(data["Close"])
        data["Vol"] = clean_numeric_volume(data["Vol"])

        # dropping rows with 'nan' values
        data.dropna(inplace=True)

        # Removing duplicate rows
        data.drop_duplicates(inplace=True)

        # sorting the dataset with symbols alphabets and date col
        data.sort_values(by=["Symbol", "Date"], inplace=True)

        data.to_csv(self.output_file, index=False)
        print(f"Preprocessing data success.\n\n File saved to : {self.output_file}")

    def run(self):
        self.setup_dates()

        with requests.Session() as session:
            token = self.get_csrf_token(session)
            print(f"Fetched CSRF token: {token}")

            # Check if the file exists
            file_exists = os.path.isfile(self.output_file)

            for date in self.generate_dates(self.start_date, self.end_date):
                time.sleep(random.uniform(1, 3))
                try:
                    html, date = self.get_html(session, date, token)
                    data = self.parse_html(html, date)
                    if data:
                        # append the scraped data after each successfull scrape
                        df = pd.DataFrame(
                            data,
                            columns=[
                                "Symbol",
                                "Date",
                                "Open",
                                "High",
                                "Low",
                                "Close",
                                "Vol",
                            ],
                        )
                        # append data to CSV file, write headers if file does not exist
                        df.to_csv(
                            self.output_file,
                            mode="a",
                            header=not file_exists,
                            index=False,
                        )
                        file_exists = True  # After the first write, file exists
                    print(f"Processed date: {date}, found data: {len(data)} entries")
                except Exception as e:
                    print(f"Error processing date {date}: {e}")

        df = pd.read_csv(self.output_file,low_memory=False)
        df.to_csv(self.output_file, index=False)
        self.format_datasets()

        print(
            f"NEPSE stocks scraped successfully from {self.start_date} - {self.end_date}\n\n File saved to {self.output_file}"
        )


if __name__ == "__main__":
    scraper = NepseStockScraper()
    scraper.run()
