from datetime import date, datetime
from flask import Flask, render_template
from finta import TA
import pandas as pd
import yfinance as yf

app = Flask(__name__)


@app.route('/')
def index():
    # python app.py

    # Start Data Pre-processing (pp)
    gold_ticker = "GC=F"
    pp_current_year = date.today().year
    pp_first_date_str = f'{pp_current_year}-01-01'
    pp_first_date = datetime.strptime(pp_first_date_str, "%Y-%m-%d")

    csv_url = 'https://drive.google.com/uc?id=1GzQP0Mt8OBiCrohC6khaywT8RAZ24ErK'
    pp_pred_csv = pd.read_csv(csv_url)

    pp_actual_data = yf.download(
        gold_ticker, start=pp_first_date, end=date.today())
    pp_actual_data.reset_index(inplace=True)
    pp_actual_data['Date'] = pp_actual_data['Date'].dt.strftime('%Y-%m-%d')
    pp_actual_data = pp_actual_data[['Date', 'Adj Close']]
    print('hi: ', pp_actual_data)

    # Find the first date of pp_pred_csv and the last date of pp_actual_data
    first_pred_date = pp_pred_csv['Date'].min()
    last_actual_date = pp_actual_data['Date'].max()
    # Filter pp_pred_csv based on the date range
    pp_pred_csv_filtered = pp_pred_csv[(pp_pred_csv['Date'] >= first_pred_date) & (
        pp_pred_csv['Date'] <= last_actual_date)]
    # Merge pp_actual_data with the filtered pp_pred_csv
    pp_actual_pred_data = pd.merge(
        pp_actual_data, pp_pred_csv_filtered, on='Date', how='left')
    # Include the rows from pp_pred_csv that are after the last date of pp_actual_data
    pp_pred_csv_after_actual = pp_pred_csv[pp_pred_csv['Date']
                                           > last_actual_date]
    pp_actual_pred_data = pd.concat(
        [pp_actual_pred_data, pp_pred_csv_after_actual], ignore_index=True)
    # Rename the 'Adj Close' column to 'Real_Gold_Price'
    pp_actual_pred_data.rename(
        columns={'Adj Close': 'Actual_Gold_Price'}, inplace=True)

    pp_actual_rsi_data = yf.download(
        gold_ticker, start=pp_first_date, end=date.today())

    if len(pp_actual_rsi_data) < 30:
        # If true, download data from the start of the previous year to today
        pp_previous_year_str = f'{pp_current_year - 1}-01-01'
        pp_previous_year = datetime.strptime(pp_previous_year_str, "%Y-%m-%d")
        pp_actual_rsi_data = yf.download(
            gold_ticker, start=pp_previous_year, end=date.today())

    pp_actual_rsi_data['RSI'] = TA.RSI(pp_actual_rsi_data)
    pp_actual_rsi_data.reset_index(inplace=True)
    pp_actual_rsi_data['Date'] = pp_actual_rsi_data['Date'].dt.strftime(
        '%Y-%m-%d')
    pp_actual_rsi_data = pp_actual_rsi_data[['Date', 'RSI']]
    pp_actual_pred_rsi_data = pd.merge(
        pp_actual_pred_data, pp_actual_rsi_data, on='Date', how='left')
    # End Data Pre-processing

    # Start Gold Prices Forecasting Chart (fc)
    first_date_with_predicted_gold_price = pp_actual_pred_rsi_data.loc[
        pp_actual_pred_rsi_data['Predicted_Gold_Price'].notnull(), 'Date'].min()
    fc_firstDay_basedOn_pred = pp_actual_pred_rsi_data[pp_actual_pred_rsi_data['Date']
                                                       >= first_date_with_predicted_gold_price]

    fc_date = fc_firstDay_basedOn_pred['Date'].tolist()
    fc_actual = fc_firstDay_basedOn_pred['Actual_Gold_Price'].tolist()
    fc_pred = fc_firstDay_basedOn_pred['Predicted_Gold_Price'].tolist()
    fc_rsi = fc_firstDay_basedOn_pred['RSI'].tolist()
    # End Gold Prices Forecastign Chart

    # Start Trade Opition (to)

    def trade_opinion(row, actual_gold_price_shifted, rsi_shifted):
        if abs(row['Predicted_Gold_Price'] - actual_gold_price_shifted) < 2:
            return 'Hold'
        elif row['Predicted_Gold_Price'] > actual_gold_price_shifted and rsi_shifted > 70:
            return 'Hold'
        elif row['Predicted_Gold_Price'] > actual_gold_price_shifted and rsi_shifted <= 70:
            return 'Buy'
        elif row['Predicted_Gold_Price'] < actual_gold_price_shifted and rsi_shifted < 30:
            return 'Hold'
        elif row['Predicted_Gold_Price'] < actual_gold_price_shifted and rsi_shifted >= 30:
            return 'Sell'
        else:
            return 'No Info'

    # Shift the Actual_Gold_Price and RSI columns
    actual_gold_price_shifted = pp_actual_pred_rsi_data['Actual_Gold_Price'].shift(
    )
    rsi_shifted = pp_actual_pred_rsi_data['RSI'].shift()

    # Apply the trade_opinion function to each row in the DataFrame
    pp_actual_pred_rsi_data['Trade_Opinion'] = pp_actual_pred_rsi_data.apply(
        lambda row: trade_opinion(row, actual_gold_price_shifted[row.name], rsi_shifted[row.name]), axis=1)

    to_current_date = datetime.today().strftime('%Y-%m-%d')
    to_current_date_row = pp_actual_pred_rsi_data.loc[pp_actual_pred_rsi_data['Date']
                                                      == to_current_date]
    if not to_current_date_row.empty:
        to_trade_opinion_value = to_current_date_row['Trade_Opinion'].values[0]

        to_today_pred = round(
            to_current_date_row['Predicted_Gold_Price'].values[0], 2)
        to_lastDay_rsi = round(
            rsi_shifted.loc[pp_actual_pred_rsi_data['Date'] == to_current_date].values[0], 2)
        to_lastDay_actual = actual_gold_price_shifted[pp_actual_pred_rsi_data['Date']
                                                      == to_current_date].values[0]

        # Start indicator of trade opinion based on predicted value for Technical indicator
        if abs(to_lastDay_actual - to_today_pred) < 2:
            to_trade_opinion_predBased = 'Hold'
        elif to_lastDay_actual < to_today_pred:
            to_trade_opinion_predBased = 'Buy'
        elif to_lastDay_actual > to_today_pred:
            to_trade_opinion_predBased = 'Sell'
        else:
            to_trade_opinion_predBased = 'Hold'
        # End indicator of trade opinion based on predicted value for Technical indicator
        # Start indicator of trade opinion based on RSI value for Technical indicator
        if to_lastDay_rsi > 70:
            to_trade_opinion_rsiBased = 'Sell'
        elif to_lastDay_rsi < 30:
            to_trade_opinion_rsiBased = 'Buy'
        else:
            to_trade_opinion_rsiBased = 'Hold'
        # End indicator of trade opinion based on RSI value for Technical indicator
    else:
        to_trade_opinion_value = 'Close Market'
        to_today_pred = 'Close Market'
        to_lastDay_rsi = 'Close Market'
        to_trade_opinion_predBased = 'Close Market'
        to_trade_opinion_rsiBased = 'Close Market'
    # End Trade Opition (to)

    # Start Winning Rate (wr)

    def calculate_winning_rate(index, row, actual_gold_price):
        if index == len(actual_gold_price) - 1:
            return None

        actual_gold_price_shifted = actual_gold_price.shift(-1)
        next_day_price = actual_gold_price_shifted[index]
        current_day_price = row['Actual_Gold_Price']
        trade_opinion = row['Trade_Opinion']

        if trade_opinion == 'Buy' and next_day_price > current_day_price:
            return 'W'
        elif trade_opinion == 'Buy' and next_day_price < current_day_price:
            return 'L'
        elif trade_opinion == 'Sell' and next_day_price > current_day_price:
            return 'L'
        elif trade_opinion == 'Sell' and next_day_price < current_day_price:
            return 'W'
        else:
            return 'N'

    actual_gold_price = pp_actual_pred_rsi_data['Actual_Gold_Price']

    # Apply the calculate_winning_rate function to each row in the DataFrame
    pp_actual_pred_rsi_data['Winning_Rate'] = pp_actual_pred_rsi_data.apply(
        lambda row: calculate_winning_rate(row.name, row, actual_gold_price), axis=1)

    wr_winning_count = pp_actual_pred_rsi_data['Winning_Rate'].value_counts()[
        'W']
    wr_losing_count = pp_actual_pred_rsi_data['Winning_Rate'].value_counts()[
        'L']

    wr_winning_rate = round(
        (wr_winning_count / (wr_winning_count + wr_losing_count))*100, 2)
    # End Winning Rate (wr)
    pd.set_option('display.max_rows', None)
    print(pp_actual_pred_rsi_data)
    return render_template('index.html',
                           fc_date=fc_date,
                           fc_pred=fc_pred,
                           fc_actual=fc_actual,
                           fc_rsi=fc_rsi,
                           to_trade_opinion_value=to_trade_opinion_value,
                           to_today_pred=to_today_pred,
                           to_lastDay_rsi=to_lastDay_rsi,
                           to_trade_opinion_predBased=to_trade_opinion_predBased,
                           to_trade_opinion_rsiBased=to_trade_opinion_rsiBased,
                           wr_winning_rate=wr_winning_rate
                           )


if __name__ == '__main__':
    app.run(debug=True)
