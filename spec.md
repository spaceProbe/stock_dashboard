# Stock Value Viewer Planning Document

## Executive Summary
A Streamlit web application to view custom stock values and perform calculations like tax costs and net/net profit.

## Background
The user needs a way to track specific stocks, monitor their real-time value, and calculate potential profits after taxes and other costs.

## Objectives
1. Monitor real-time stock prices using the yfinance API.
2. Calculate tax costs and estimate net profit for holdings.
3. Visualize historical performance with charts.
4. Manage holdings through manual entry with persistence in YAML format.

## Scope
### In Scope
- Real-time price monitoring via yfinance.
- Tax and net profit calculation engine.
- Historical performance charting.
- YAML-based portfolio management.
### Out of Scope
- Support for crypto or other non-stock assets (unless via yfinance).
- Integration with brokerage APIs for automatic trade execution.

## Requirements
### Functional Requirements
- Fetch data from yfinance API.
- Display current price and daily change.
- Calculate taxes based on user-defined rates.
- Estimate net profit after all costs/taxes.
- Visualize stock performance over time.
- Allow manual entry of stock symbols and quantities.
- Save and load holdings from a YAML file.

### Non-Functional Requirements
- Simple and intuitive UI using Streamlit.
- Fast data retrieval.

## Architecture Overview
- Frontend/Backend: Streamlit (Python)
- Data Source: yfinance API
- Persistence: YAML files

## Implementation Plan
### Phase 1: Core MVP
- Timeline: TBD
- Deliverables: Basic Streamlit app with yfinance integration and YAML loading.
- Dependencies: streamlit, yfinance, pyyaml

## Tools & Technologies
- Python
- Streamlit
- yfinance
- PyYAML

## Open Questions
- [ ] What specific tax rates/rules should be implemented initially?
- [ ] Should we support multiple portfolios in different YAML files?

---
*Document Status: Draft*  
*Last Updated: 2026-04-15*  
*Author: opencode*
