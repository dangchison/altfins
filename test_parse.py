import sys
from telegram import parse_trade_setup

raw_text = """TIA - Apr 08, 2026 - Trade setup: Price is consolidating in a Sideways Channel ($0.30 - $0.38). We wait for a breakout, either bullish above $0.38 to signal a trend reversal, or bearish below $0.30 support, which would signal resumption of Downtrend. Swing traders can trade the Sideways Channel (Buy near $0.30 support, Sell near $0.38 resistance). (Set a price alert) TIA was also featured in our Coin Picks research. Read here. Learn to trade breakouts in Lesson 7 and Risk Management in Lesson 9.
Pattern: Price is trading in a Sideways Channel , which is a neutral pattern (indication of market indecision). Trend Traders ought to wait for a breakout in either direction, although typically it breaks in the direction of the existing trend. Swing Traders can trade the range - Buy near Support and Sell near Resistance. Learn to trade Sideways Channel in Lesson 6.
Trend: Short-term trend is Down, Medium-term trend is Strong Down, Long-term trend is Strong Down.
Momentum: Price is neither overbought nor oversold currently, based on RSI-14 levels (RSI > 30 and RSI < 70).
Support and Resistance: Nearest Support Zone is $0.27.
Nearest Resistance Zone is $0.35, then $0.45."""

print(parse_trade_setup(raw_text))
