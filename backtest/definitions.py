import os
from .support import check_dir, check_file

# Main definitions
INSTANTS = ["bod", "bod_adjusted", "post_open", "pre_close", "eod"]

# DIRECTORIES
ASSETS_DATA = check_dir(os.path.join("data","assets"))
SERIES_DATA = check_dir(os.path.join("data","series"))
RESULTS_DATA = check_dir(os.path.join("data","results"))
SECTORS_DATA = check_dir(os.path.join("data","sectors"))
MKT_PORTFOLIO_DATA = check_dir(os.path.join("data","mkt_portfolio"))

# ANALYSIS
EXPORTED_DATA = check_dir(os.path.join(RESULTS_DATA,"exported"))


# FILES
RISK_FREE_RATE = check_file(os.path.join(SERIES_DATA, "risk_free_rate.csv"))
MKT_PORTFOLIO = check_file(os.path.join(MKT_PORTFOLIO_DATA, "daily_portfolio.csv"))
SECTORS = check_file(os.path.join(SECTORS_DATA, "sectors.csv"))

# AMAGO FUNDS
AMAGO_MASTER_CNPJ = "29.562.526/0001-47"
AMAGO_FIP1_CNPJ = "29.562.563/0001-55"
