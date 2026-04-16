import yaml
import os

class PortfolioManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.holdings = self.load_holdings()

    def load_holdings(self):
        if not os.path.exists(self.filepath):
            return []
        with open(self.filepath, 'r') as f:
            try:
                data = yaml.safe_load(f)
                return data.get('holdings', []) if data else []
            except yaml.YAMLError:
                return []

    def save_holdings(self, holdings):
        self.holdings = holdings
        with open(self.filepath, 'w') as f:
            yaml.dump({'holdings': holdings}, f)

    def add_holding(self, ticker, quantity, purchase_price, basis_adjustment=0.0):
        new_holding = {
            'ticker': ticker.upper(),
            'quantity': float(quantity),
            'purchase_price': float(purchase_price),
            'basis_adjustment': float(basis_adjustment)
        }
        self.holdings.append(new_holding)
        self.save_holdings(self.holdings)

    def update_holding(self, ticker, quantity, purchase_price, basis_adjustment):
        for h in self.holdings:
            if h['ticker'].upper() == ticker.upper():
                h['quantity'] = float(quantity)
                h['purchase_price'] = float(purchase_price)
                h['basis_adjustment'] = float(basis_adjustment)
                self.save_holdings(self.holdings)
                return True
        return False
