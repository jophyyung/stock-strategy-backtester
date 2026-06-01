import yfinance as yf

# Download 1 year of Apple stock data
data = yf.download("AAPL", period="1y")

print("Number of rows:", len(data))
print("\nFirst 5 rows:")
print(data.head())