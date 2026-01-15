import akshare as ak
symbol = "600580"
try:
    df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="主要指标")
    print("Columns:", df.columns.tolist())
    print("First few rows:")
    print(df.head(20))
except Exception as e:
    print(f"Error: {e}")
