#!/usr/bin/env python3
"""
scrape_ibkr_account.py - Extract YOUR data from Interactive Brokers

Extracts from your connected IBKR account:
1. Portfolio holdings (positions, quantities, costs, current values)
2. Trade history (all executed trades with P&L)
3. Account statements (balances, cash, margin)
4. Market data (for your holdings)

NO account credentials needed - connects to your running TWS/Gateway session.

Requirements:
- IBKR account logged into TWS or IB Gateway
- API enabled in TWS settings

Usage:
    python scrape_ibkr_account.py                # extract everything
    python scrape_ibkr_account.py --portfolio    # just current positions
    python scrape_ibkr_account.py --trades       # just trade history
    python scrape_ibkr_account.py --since 2024-01-01  # trades since date
"""

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta
import json
import csv

try:
    from ib_insync import IB, Stock, util
except ImportError:
    print("Error: ib_insync not installed")
    print("Install with: pip install ib_insync")
    sys.exit(1)

import store

# IBKR connection settings
IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4001  # IB Gateway Paper: 4001 (Gateway Live: 4002, TWS: 7496/7497)
CLIENT_ID = 2  # Different from scraper to avoid conflicts


def connect_ibkr():
    """Connect to IBKR TWS or Gateway."""
    ib = IB()
    try:
        ib.connect(IBKR_HOST, IBKR_PORT, clientId=CLIENT_ID, timeout=10)
        print(f"✓ Connected to IBKR at {IBKR_HOST}:{IBKR_PORT}")
        return ib
    except Exception as e:
        print(f"✗ Failed to connect to IBKR: {e}")
        print("\nMake sure TWS or IB Gateway is running and you're logged in:")
        print("  - TWS Paper Trading: localhost:7497")
        print("  - TWS Live Trading: localhost:7496")
        print("  - IB Gateway: localhost:4001 (paper) or 4002 (live)")
        sys.exit(1)


def export_portfolio(ib, db):
    """Extract current portfolio positions."""
    print("\n" + "="*60)
    print("PORTFOLIO HOLDINGS")
    print("="*60)
    
    positions = ib.positions()
    
    if not positions:
        print("No positions found")
        return
    
    print(f"\nFound {len(positions)} positions:\n")
    
    portfolio_data = []
    for pos in positions:
        contract = pos.contract
        
        # Get current market price
        ib.qualifyContracts(contract)
        ticker = ib.reqMktData(contract, '', False, False)
        ib.sleep(1)  # Wait for price update
        
        market_price = ticker.marketPrice() if ticker.marketPrice() == ticker.marketPrice() else ticker.last
        
        position_value = pos.position * market_price if market_price else 0
        unrealized_pnl = pos.unrealizedPNL
        
        data = {
            'symbol': contract.symbol,
            'position': pos.position,
            'avg_cost': pos.avgCost,
            'market_price': market_price,
            'market_value': position_value,
            'unrealized_pnl': unrealized_pnl,
            'account': pos.account,
            'timestamp': datetime.now().isoformat()
        }
        
        portfolio_data.append(data)
        
        print(f"{contract.symbol:10} | Qty: {pos.position:>8.2f} | Avg Cost: ${pos.avgCost:>10.2f} | "
              f"Market: ${market_price:>10.2f} | Value: ${position_value:>12.2f} | "
              f"P&L: ${unrealized_pnl:>10.2f}")
        
        ib.cancelMktData(contract)
    
    # Save to JSON
    with open('ibkr_portfolio.json', 'w') as f:
        json.dump(portfolio_data, f, indent=2)
    
    print(f"\n✓ Exported {len(positions)} positions to ibkr_portfolio.json")
    
    # Store in database as metrics
    for data in portfolio_data:
        date = datetime.now().strftime('%Y-%m-%d')
        
        # Find company in database by ticker
        company_row = db.execute(
            "SELECT name FROM companies WHERE ticker = ?", 
            (data['symbol'],)
        ).fetchone()
        
        if company_row:
            company = company_row[0]
            store.add_metric(db, company, 'portfolio_quantity', date, data['position'], 'shares', 'IBKR')
            store.add_metric(db, company, 'portfolio_cost', date, data['avg_cost'], 'USD', 'IBKR')
            store.add_metric(db, company, 'portfolio_value', date, data['market_value'], 'USD', 'IBKR')
            store.add_metric(db, company, 'portfolio_pnl', date, data['unrealized_pnl'], 'USD', 'IBKR')
    
    return portfolio_data


def export_trades(ib, db, since_date=None):
    """Extract trade execution history."""
    print("\n" + "="*60)
    print("TRADE HISTORY")
    print("="*60)
    
    # Request execution history
    executions = ib.reqExecutions()
    
    if not executions:
        print("No executions found")
        return
    
    # Filter by date if specified
    if since_date:
        since_dt = datetime.fromisoformat(since_date)
        executions = [e for e in executions if e.time >= since_dt]
    
    print(f"\nFound {len(executions)} executions:\n")
    
    trades_data = []
    for exec in executions:
        contract = exec.contract
        execution = exec.execution
        
        data = {
            'symbol': contract.symbol,
            'side': execution.side,
            'quantity': execution.shares,
            'price': execution.price,
            'time': execution.time.isoformat(),
            'exchange': execution.exchange,
            'order_id': execution.orderId,
            'exec_id': execution.execId,
            'account': execution.acctNumber
        }
        
        trades_data.append(data)
        
        print(f"{execution.time.strftime('%Y-%m-%d %H:%M:%S')} | {contract.symbol:10} | "
              f"{execution.side:4} | {execution.shares:>8.2f} @ ${execution.price:>10.2f}")
    
    # Save to CSV
    if trades_data:
        with open('ibkr_trades.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trades_data[0].keys())
            writer.writeheader()
            writer.writerows(trades_data)
        
        print(f"\n✓ Exported {len(trades_data)} trades to ibkr_trades.csv")
    
    return trades_data


def export_account_summary(ib, db):
    """Extract account balances and summary."""
    print("\n" + "="*60)
    print("ACCOUNT SUMMARY")
    print("="*60)
    
    account_values = ib.accountValues()
    
    summary = {}
    for item in account_values:
        summary[item.tag] = {
            'value': item.value,
            'currency': item.currency,
            'account': item.account
        }
    
    # Print key metrics
    print(f"\nAccount: {account_values[0].account if account_values else 'N/A'}\n")
    
    key_metrics = [
        'NetLiquidation',
        'TotalCashValue', 
        'GrossPositionValue',
        'UnrealizedPnL',
        'RealizedPnL',
        'BuyingPower'
    ]
    
    for metric in key_metrics:
        if metric in summary:
            val = summary[metric]
            print(f"{metric:20} : {val['currency']} {float(val['value']):>15,.2f}")
    
    # Save to JSON
    with open('ibkr_account_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ Exported account summary to ibkr_account_summary.json")
    
    # Store key metrics in database
    date = datetime.now().strftime('%Y-%m-%d')
    
    # Store account-level metrics (no specific company)
    # We'll create a special "PORTFOLIO" company for account-level data
    db.execute("INSERT OR IGNORE INTO companies (name, ticker) VALUES ('PORTFOLIO', 'PORTFOLIO')")
    db.commit()
    
    for metric in key_metrics:
        if metric in summary:
            value = float(summary[metric]['value'])
            currency = summary[metric]['currency']
            store.add_metric(db, 'PORTFOLIO', metric.lower(), date, value, currency, 'IBKR')
    
    return summary


def main():
    ap = argparse.ArgumentParser(description="Extract YOUR data from IBKR")
    ap.add_argument("--db", default=store.DB_PATH)
    ap.add_argument("--portfolio", action="store_true", help="Export portfolio only")
    ap.add_argument("--trades", action="store_true", help="Export trades only")
    ap.add_argument("--account", action="store_true", help="Export account summary only")
    ap.add_argument("--since", help="Trade history since date (YYYY-MM-DD)")
    args = ap.parse_args()
    
    print("IBKR Account Data Extractor")
    print("="*60)
    print("Connecting to your IBKR account...")
    
    # Connect to IBKR
    ib = connect_ibkr()
    
    # Connect to database
    db = store.get_db(args.db)
    
    # Determine what to export
    export_all = not (args.portfolio or args.trades or args.account)
    
    results = {}
    
    if args.portfolio or export_all:
        results['portfolio'] = export_portfolio(ib, db)
    
    if args.trades or export_all:
        results['trades'] = export_trades(ib, db, args.since)
    
    if args.account or export_all:
        results['summary'] = export_account_summary(ib, db)
    
    ib.disconnect()
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE")
    print("="*60)
    print("\nFiles created:")
    if 'portfolio' in results:
        print("  - ibkr_portfolio.json")
    if 'trades' in results:
        print("  - ibkr_trades.csv")
    if 'summary' in results:
        print("  - ibkr_account_summary.json")
    print(f"\nData also stored in {args.db}")
    print("\nRun this script regularly to keep your local copy updated!")


if __name__ == '__main__':
    main()
