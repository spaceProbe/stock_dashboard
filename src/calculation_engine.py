import pandas as pd

class CalculationEngine:
    @staticmethod
    def calculate_metrics(holding, current_price):
        if current_price is None:
            return None

        quantity = holding['quantity']
        purchase_price = holding['purchase_price']
        basis_adjustment = holding.get('basis_adjustment', 0.0)

        market_value = quantity * current_price
        # Total cost basis includes the original purchase price plus any manual adjustment
        cost_basis = (quantity * purchase_price) + basis_adjustment
        unrealized_pnl = market_value - cost_basis

        # Calculate tiered long-term capital gains tax
        tax_cost = 0.0
        if unrealized_pnl > 0:
            gain = unrealized_pnl
            if gain > 613700:
                tax_cost = (gain - 613700) * 0.20 + (613700 - 98900) * 0.15
            elif gain > 98900:
                tax_cost = (gain - 98900) * 0.15
            else:
                tax_cost = 0.0

        net_profit = unrealized_pnl - tax_cost

        return {
            'market_value': market_value,
            'unrealized_pnl': unrealized_pnl,
            'tax_cost': tax_cost,
            'net_profit': net_profit
        }
