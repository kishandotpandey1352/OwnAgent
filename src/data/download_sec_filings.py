from sec_edgar_downloader import Downloader

dl = Downloader(
    "data/raw/sec",
    "your-email@example.com"
)

companies = ["AAPL", "MSFT", "NVDA", "JPM", "GS"]

for ticker in companies:
    print(f"Downloading {ticker}...")
    dl.get(
        "10-K",
        ticker,
        limit=3
    )

print("Done.")