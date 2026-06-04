# Marking the Close Detection

**Document ID:** marking_the_close_detection
**Source:** Trading Technologies Trade Surveillance
**URL:** https://library.tradingtechnologies.com/tt-trade-surveillance/inv-marking-the-close.html
**Document Type:** surveillance_detection

## Definition

Marking the Close is a market manipulation strategy in which a trader attempts to influence the settlement price of a financial instrument during the settlement period.

The objective is to artificially move the closing or settlement price in a favorable direction.

## Detection Objective

The surveillance system identifies trading activity that may have influenced the final settlement price.

Detection focuses on trading behavior during the official settlement window defined by the exchange.

## Key Detection Signals

### Trader Vs Session

Percentage of the trader's total daily activity that occurred during the settlement period.

High values may indicate deliberate concentration of trading activity near settlement.

### Vol Vs Market

Trader settlement volume as a percentage of total market settlement volume.

A high value suggests the trader may have had significant influence on the settlement price.

### Buy/Sell Imbalance

Large concentration of activity on one side of the market:

* predominantly buys during upward price movement;
* predominantly sells during downward price movement.

### Aggressive Trading

High percentage of aggressor fills during settlement.

Aggressive order submission is considered more suspicious than passive execution.

### Price Movement During Settlement

Difference between:

* last market price before settlement;
* final settlement price.

Large movements may indicate possible manipulation.

### Trader VWAP vs Settlement Price

Comparison between:

* trader VWAP;
* final settlement price.

Small differences may suggest successful influence on settlement.

## Surveillance Metrics

The model analyzes:

* settlement price;
* trader volume;
* market volume;
* VWAP;
* aggressor fill percentage;
* buy/sell fill ratio;
* settlement start time;
* settlement end time;
* price movement in ticks.

## Risk Scoring

The surveillance model produces a score from 0 to 100.

### High-Risk Threshold

Scores above 75 indicate elevated manipulation risk and should receive additional review.

## Investigation Indicators

Potential warning signs include:

* large percentage of settlement volume;
* concentration of trading during settlement;
* aggressive order entry;
* one-sided trading activity;
* significant settlement-period price movement.

## Key Concepts

* Marking the Close
* Settlement Price Manipulation
* Settlement Window
* VWAP
* Trader Volume
* Market Volume
* Aggressor Orders
* Surveillance Models
* Market Abuse Detection
* Compliance Monitoring
