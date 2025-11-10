import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os # 引入 os 模組用於檢查本地檔案是否存在

# 設置中文字體，如果您的執行環境不是 Windows，可能需要修改此處
try:
    plt.rcParams['font.family'] = 'Microsoft JhengHei'
except:
    # 針對非 Windows 環境的備用設置，如 Mac/Linux
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS'] # 適用於多數非Windows環境
    plt.rcParams['axes.unicode_minus'] = False # 解決負號亂碼

# ========================================================
# Streamlit 應用程式設定與標題
# ========================================================
st.set_page_config(page_title="台股加權指數回測系統", layout="wide")
st.title("📈 台股加權指數回測系統")

# 【🚨 檔案讀取與選擇區塊 - 核心修改部分 🚨】
DATA_FILE_LOCAL = '加權指數資料.xlsx'
df = None
data_source = None

# 在側邊欄提供選項，預設為本地讀取 (index=0)
data_load_mode = st.sidebar.radio(
    "選擇資料來源", 
    ("從本地檔案讀取 (加權指數資料.xlsx)", "手動上傳 Excel 檔案"),
    index=0 
)

st.markdown("---") # 分隔線

if data_load_mode == "從本地檔案讀取 (加權指數資料.xlsx)":
    st.info(f"資料來源模式：**本地檔案**。請確認 **{DATA_FILE_LOCAL}** 存在於專案目錄。")
    if os.path.exists(DATA_FILE_LOCAL):
        try:
            df = pd.read_excel(DATA_FILE_LOCAL)
            data_source = DATA_FILE_LOCAL
        except Exception as e:
            st.error(f"❌ 錯誤：讀取本地檔案失敗，請檢查檔案格式。錯誤訊息: {e}")
            df = None
    else:
        st.warning(f"⚠️ 警告：專案目錄中找不到檔案 **{DATA_FILE_LOCAL}**。請將檔案上傳或切換為「手動上傳」模式。")

elif data_load_mode == "手動上傳 Excel 檔案":
    st.info("資料來源模式：**手動上傳**。")
    uploaded_file = st.file_uploader("請上傳加權指數Excel檔案 (格式：日期, 收盤價)", type=["xlsx"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            data_source = uploaded_file.name
        except Exception as e:
            st.error(f"❌ 錯誤：處理上傳檔案失敗，請檢查檔案格式。錯誤訊息: {e}")
            df = None
    else:
        st.warning("⚠️ 警告：請上傳檔案以開始回測。")


# ========================================================
# 應用程式主體：檢查檔案是否成功讀取後才執行
# ========================================================

if data_source and df is not None and not df.empty:
    
    # 確保資料格式正確
    df.columns = ['日期', '收盤價']
    df['日期'] = pd.to_datetime(df['日期'])
    df = df.sort_values('日期').reset_index(drop=True)

    available_years = sorted(list(set(df['日期'].dt.year)))
    start_year = st.sidebar.selectbox("選擇回測開始年份", options=["全部"] + available_years, index=0)
    end_year = st.sidebar.selectbox("選擇回測結束年份", options=["全部"] + available_years[::-1], index=0)

    # 修正：只有年份都不是"全部"時才做篩選，且保證型態正確
    if start_year != "全部" and end_year != "全部":
        df = df[(df['日期'].dt.year >= int(start_year)) & (df['日期'].dt.year <= int(end_year))].reset_index(drop=True)

    # ====== 參數設定 ======
    auto_opt = st.sidebar.checkbox("自動優化均線天數", value=False)
    if auto_opt:
        min_ma = st.sidebar.number_input("均線天數-起始", min_value=2, max_value=200, value=5, step=1)
        max_ma = st.sidebar.number_input("均線天數-結束", min_value=2, max_value=200, value=60, step=1)
        ma_range = range(min_ma, max_ma + 1)
        moving_avg_days = None  # 後續由優化器決定
    else:
        moving_avg_days = st.sidebar.number_input("輸入幾日線", min_value=2, max_value=500, value=13, step=1)
    strategy_mode = st.sidebar.selectbox("選擇回測模式", ("雙向：站上多、跌破空", "只做多", "只做空", "從頭抱到尾"))
    start_capital = st.sidebar.number_input("輸入初始資金 (元)", value=1000000, step=50000)
    monthly_invest = st.sidebar.number_input("每月定期投入金額 (元)", value=0, step=1000)
    leverage = st.sidebar.number_input("固定口數槓桿倍率", value=2.0, step=0.5)
    dynamic_leverage = st.sidebar.number_input("動態口數槓桿倍率", value=2.0, step=0.5)
    point_value = st.sidebar.number_input("每點價值 (元)", value=50, step=10)
    lot_mode = st.sidebar.selectbox("口數設定模式", ("固定口數", "資金動態口數"), index=1)
    fixed_lots = st.sidebar.number_input("固定口數 (張數)", value=1, step=1)
    # ====== 交易成本設定 ======
    use_fee = st.sidebar.checkbox("納入交易成本", value=True)
    buy_fee = st.sidebar.number_input("每口買進手續費", value=35, step=1)
    sell_fee = st.sidebar.number_input("每口賣出手續費", value=35, step=1)
    # ====== Monte Carlo 模擬設定 ======
    do_mc = st.sidebar.checkbox("Monte Carlo 模擬", value=False)
    mc_sim_round = st.sidebar.number_input("Monte Carlo模擬次數", value=500, min_value=100, max_value=2000, step=100)
    mc_seed = st.sidebar.number_input("Monte Carlo隨機種子", value=42, step=1)
    remove_low_pct = st.sidebar.number_input("去除前幾%最低值", min_value=0, max_value=40, value=5, step=1)
    remove_high_pct = st.sidebar.number_input("去除後幾%最高值", min_value=0, max_value=40, value=5, step=1)
    
    # ====== 新增：自選績效指標設定 ======
    st.sidebar.markdown("---")
    st.sidebar.subheader("🛠️ 績效指標客製化")
    
    available_metrics = {
        "總交易次數": "num_trades",
        "勝率 (%)": "win_rate",
        "獲利次數": "num_wins",
        "虧損次數": "num_losses",
        "平均獲利金額": "avg_profit",
        "平均虧損金額": "avg_loss",
        "風險報酬比 (R/R)": "risk_reward_ratio",
        "最大虧損 (MDD)": "max_dd_value",
        "最大單筆報酬率": "max_gain_pct",
        "最大單筆虧損率": "max_loss_pct",
        "總交易持有天數": "total_days",
    }
    
    # 預設選中所有項目
    selected_metrics_keys = st.sidebar.multiselect(
        "選擇要顯示的績效指標",
        options=list(available_metrics.keys()),
        default=list(available_metrics.keys())
    )
    
    # 將選中的指標轉換為內部使用的 key
    selected_metrics_map = {available_metrics[k]: k for k in selected_metrics_keys}
    
    # ==================================


    # ====== 參數優化主體 ======
    def backtest(moving_avg_days):
        df_bt = df.copy()
        df_bt[f'{moving_avg_days}日線'] = df_bt['收盤價'].rolling(window=moving_avg_days).mean()
        trades, capital_history, capital_date, index_history = [], [], [], []
        capital = start_capital
        holding = False
        position = None
        entry_price = None
        entry_date = None
        last_month = df_bt.iloc[0]['日期'].month
        for i in range(1, len(df_bt)):
            this_month = df_bt.loc[i, '日期'].month
            if monthly_invest > 0 and this_month != last_month:
                capital += monthly_invest
            last_month = this_month
            # 修正 1: 移除 f-string 結尾多餘的 }
            if pd.isna(df_bt.loc[i, f'{moving_avg_days}日線']):
                capital_history.append(capital)
                capital_date.append(df_bt.loc[i, '日期'])
                index_history.append(df_bt.loc[i, '收盤價'])
                continue
            action = df_bt.loc[i, '收盤價'] - df_bt.loc[i, f'{moving_avg_days}日線']
            current_price = df_bt.loc[i, '收盤價']
            date = df_bt.loc[i, '日期']
            if not holding:
                if strategy_mode == "只做多" and action > 0:
                    holding = True
                    position = '多'
                    entry_price = current_price
                    entry_date = date
                elif strategy_mode == "只做空" and action < 0:
                    holding = True
                    position = '空'
                    entry_price = current_price
                    entry_date = date
                elif strategy_mode == "雙向：站上多、跌破空" and action != 0:
                    holding = True
                    position = '多' if action > 0 else '空'
                    entry_price = current_price
                    entry_date = date
            else:
                if strategy_mode == "只做多" and action < 0 and position == '多':
                    lots = fixed_lots if lot_mode == "固定口數" else max(
                        int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
                    fee = (buy_fee + sell_fee) * lots if use_fee else 0
                    profit = (current_price - entry_price) * lots * point_value - fee
                    capital += profit
                    holding = False
                    position = None
                    entry_price = None
                    entry_date = None
                elif strategy_mode == "只做空" and action > 0 and position == '空':
                    lots = fixed_lots if lot_mode == "固定口數" else max(
                        int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
                    fee = (buy_fee + sell_fee) * lots if use_fee else 0
                    profit = (entry_price - current_price) * lots * point_value - fee
                    capital += profit
                    holding = False
                    position = None
                    entry_price = None
                    entry_date = None
                elif strategy_mode == "雙向：站上多、跌破空":
                    if position == '多' and action < 0:
                        lots = fixed_lots if lot_mode == "固定口數" else max(
                            int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
                        fee = (buy_fee + sell_fee) * lots if use_fee else 0
                        profit = (current_price - entry_price) * lots * point_value - fee
                        capital += profit
                        holding = True
                        position = '空'
                        entry_price = current_price
                        entry_date = date
                    elif position == '空' and action > 0:
                        lots = fixed_lots if lot_mode == "固定口數" else max(
                            int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
                        fee = (buy_fee + sell_fee) * lots if use_fee else 0
                        profit = (entry_price - current_price) * lots * point_value - fee
                        capital += profit
                        holding = True
                        position = '多'
                        entry_price = current_price
                        entry_date = date
            capital_history.append(capital)
            capital_date.append(date)
            index_history.append(current_price)
        total_return = (capital_history[-1] - start_capital) / start_capital * 100
        return total_return, capital_history, capital_date, index_history

    # ====== 自動優化均線天數 ======
    if auto_opt:
        st.subheader("🔎 自動優化均線天數")
        results = []
        bar = st.progress(0)
        for idx, ma in enumerate(ma_range):
            try:
                r, _, _, _ = backtest(ma)
                results.append({'均線天數': ma, '累積報酬率': r})
            except Exception as e:
                results.append({'均線天數': ma, '累積報酬率': np.nan})
            bar.progress((idx+1)/len(ma_range))
        bar.empty()
        results_df = pd.DataFrame(results)
        best_row = results_df.loc[results_df['累積報酬率'].idxmax()]
        st.success(f"最佳均線天數：{int(best_row['均線天數'])}，累積報酬率：{best_row['累積報酬率']:.2f}%")
        fig_opt, ax_opt = plt.subplots(figsize=(10,4))
        ax_opt.plot(results_df['均線天數'], results_df['累積報酬率'])
        ax_opt.set_xlabel("均線天數")
        ax_opt.set_ylabel("累積報酬率(%)")
        ax_opt.set_title("不同均線天數累積報酬率")
        st.pyplot(fig_opt)
        st.dataframe(results_df.style.format({'累積報酬率': '{:.2f}'}), use_container_width=True)
        moving_avg_days = int(best_row['均線天數'])
        st.info(f"後續回測與模擬將自動採用「最佳均線天數」：{moving_avg_days}日線")
    df[f'{moving_avg_days}日線'] = df['收盤價'].rolling(window=moving_avg_days).mean()

    # ===== 最新市場判斷 =====
    st.subheader("🔍 最新市場判斷")
    latest_price = df.iloc[-1]['收盤價']
    latest_date_str = df.iloc[-1]['日期'].strftime('%Y-%m-%d')
    st.markdown(f"""
        - 最新日期：**{latest_date_str}**
        - 最新收盤價：**{latest_price:,.2f}**
        - 最新 {moving_avg_days} 日線：**{df.iloc[-1][f'{moving_avg_days}日線']:.2f}**
        """)
    diff = latest_price - df.iloc[-1][f'{moving_avg_days}日線']
    if latest_price > df.iloc[-1][f'{moving_avg_days}日線']:
        st.success(f"📈 現在收盤價高於 {moving_avg_days} 日線 ({diff:.2f}) ➜ **建議：做多**")
    else:
        st.error(f"📉 現在收盤價低於 {moving_avg_days} 日線 ({diff:.2f}) ➜ **建議：做空**")

    # ===== 多空建議趨勢圖 =====
    st.subheader("📊 近 100 日多空建議趨勢圖")
    if len(df) >= 100:
        recent_df = df.iloc[-100:].copy()
        recent_df['建議方向'] = recent_df.apply(
            lambda row: 1 if row['收盤價'] > row[f'{moving_avg_days}日線'] else -1, axis=1
        )
        recent_df['簡化日期'] = recent_df['日期'].dt.strftime('%m-%d')
        fig, ax = plt.subplots(figsize=(16, 4))
        ax.bar(
            recent_df['簡化日期'],
            recent_df['建議方向'],
            color=recent_df['建議方向'].map({1: '#90ee90', -1: '#ffb6c1'}) # 綠色做多，紅色做空
        )
        ax.axhline(0, color='black', linewidth=1)
        ax.set_ylabel('建議方向')
        ax.set_title('近 100 日每日多空建議（1=做多, -1=做空）')
        ax.set_xticks(range(0, 100, 10))
        ax.set_xticklabels(recent_df['簡化日期'].iloc[::10], rotation=45)
        st.pyplot(fig)
    else:
        st.warning("資料不足 100 天，無法繪製圖表。")

    # ===== 多空建議統計條 =====
    st.subheader("📊 近 100 日建議方向統計")
    if len(df) >= 100:
        long_days = (recent_df['建議方向'] == 1).sum()
        short_days = (recent_df['建議方向'] == -1).sum()
        total = long_days + short_days
        st.markdown(f"""
        <div style="font-size:15px;">
            <b>建議「做多」天數：{long_days} 天</b>
            <div style="background:#eee;height:18px;border-radius:6px;">
                <div style="width:{long_days / total * 100}%;background:#90ee90;height:100%;border-radius:6px;"></div>
            </div>
            <b>建議「做空」天數：{short_days} 天</b>
            <div style="background:#eee;height:18px;border-radius:6px;">
                <div style="width:{short_days / total * 100}%;background:#ffb6c1;height:100%;border-radius:6px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("資料不足 100 天，無法統計。")

    # ===== 回測主邏輯 =====
    trades, capital_history, capital_date, index_history = [], [], [], []
    capital = start_capital
    yearly_lots = {}
    last_month = df.iloc[0]['日期'].month

    if strategy_mode == "從頭抱到尾":
        entry_price = df.iloc[0]['收盤價']
        entry_date = df.iloc[0]['日期']
        lots = fixed_lots if lot_mode == "固定口數" else max(
            int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
        fee = (buy_fee + sell_fee) * lots if use_fee else 0
        trades.append({
            '進場日期': entry_date, '出場日期': df.iloc[-1]['日期'],
            '方向': '多', '持有天數': (df.iloc[-1]['日期'] - entry_date).days,
            '進場價': entry_price, '出場價': df.iloc[-1]['收盤價'],
            '交易口數': lots, '交易成本(元)': fee,
            '損益金額(元)': round((df.iloc[-1]['收盤價'] - entry_price) * lots * point_value - fee, 2),
            '累積資金(元)': round(capital + (df.iloc[-1]['收盤價'] - entry_price) * lots * point_value - fee, 2)
        })
        for i in range(1, len(df)):
            this_month = df.loc[i, '日期'].month
            if monthly_invest > 0 and this_month != last_month:
                capital += monthly_invest
            last_month = this_month
            price = df.loc[i, '收盤價']
            prev_price = df.loc[i - 1, '收盤價']
            profit = (price - prev_price) * lots * point_value
            capital += profit
            capital_history.append(capital)
            capital_date.append(df.loc[i, '日期'])
            index_history.append(price)
        year = entry_date.year
        yearly_lots[year] = yearly_lots.get(year, 0) + lots
    else:
        holding = False
        position = None
        entry_price = None
        entry_date = None
        last_month = df.iloc[0]['日期'].month
        for i in range(1, len(df)):
            this_month = df.loc[i, '日期'].month
            if monthly_invest > 0 and this_month != last_month:
                capital += monthly_invest
            last_month = this_month
            # 修正 2: 移除 f-string 結尾多餘的 }
            if pd.isna(df.loc[i, f'{moving_avg_days}日線']):
                capital_history.append(capital)
                capital_date.append(df.loc[i, '日期'])
                index_history.append(df.loc[i, '收盤價'])
                continue
            action = df.loc[i, '收盤價'] - df.loc[i, f'{moving_avg_days}日線']
            current_price = df.loc[i, '收盤價']
            date = df.loc[i, '日期']
            if not holding:
                if strategy_mode == "只做多" and action > 0:
                    holding = True
                    position = '多'
                    entry_price = current_price
                    entry_date = date
                elif strategy_mode == "只做空" and action < 0:
                    holding = True
                    position = '空'
                    entry_price = current_price
                    entry_date = date
                elif strategy_mode == "雙向：站上多、跌破空" and action != 0:
                    holding = True
                    position = '多' if action > 0 else '空'
                    entry_price = current_price
                    entry_date = date
            else:
                # 處理平倉邏輯
                is_closed = False
                if strategy_mode == "只做多" and action < 0 and position == '多':
                    is_closed = True
                elif strategy_mode == "只做空" and action > 0 and position == '空':
                    is_closed = True
                elif strategy_mode == "雙向：站上多、跌破空":
                    if position == '多' and action < 0:
                        is_closed = True
                        new_position = '空'
                    elif position == '空' and action > 0:
                        is_closed = True
                        new_position = '多'
                
                if is_closed:
                    lots = fixed_lots if lot_mode == "固定口數" else max(
                        int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
                    fee = (buy_fee + sell_fee) * lots if use_fee else 0
                    
                    if position == '多':
                        profit = (current_price - entry_price) * lots * point_value - fee
                    else:
                        profit = (entry_price - current_price) * lots * point_value - fee
                        
                    capital += profit
                    
                    trades.append({
                        '進場日期': entry_date, '出場日期': date,
                        '方向': position, '持有天數': (date - entry_date).days,
                        '進場價': entry_price, '出場價': current_price,
                        '交易口數': lots, '交易成本(元)': fee,
                        '損益金額(元)': round(profit, 2),
                        '累積資金(元)': round(capital, 2)
                    })
                    year = entry_date.year
                    yearly_lots[year] = yearly_lots.get(year, 0) + lots
                    
                    # 雙向策略需要轉換部位
                    if strategy_mode == "雙向：站上多、跌破空":
                        holding = True
                        position = new_position
                        entry_price = current_price
                        entry_date = date
                    else:
                        holding = False
                        position = None
                        entry_price = None
                        entry_date = None
                        
            capital_history.append(capital)
            capital_date.append(date)
            index_history.append(current_price)
            
        # 處理回測結束時的未平倉部位
        if holding and strategy_mode != "從頭抱到尾":
            lots = fixed_lots if lot_mode == "固定口數" else max(
                int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
            fee = (buy_fee + sell_fee) * lots if use_fee else 0
            
            if position == '多':
                profit = (df.iloc[-1]['收盤價'] - entry_price) * lots * point_value - fee
            else:
                profit = (entry_price - df.iloc[-1]['收盤價']) * lots * point_value - fee
            
            capital += profit
            
            trades.append({
                '進場日期': entry_date, '出場日期': df.iloc[-1]['日期'],
                '方向': position, '持有天數': (df.iloc[-1]['日期'] - entry_date).days,
                '進場價': entry_price, '出場價': df.iloc[-1]['收盤價'],
                '交易口數': lots, '交易成本(元)': fee,
                '損益金額(元)': round(profit, 2),
                '累積資金(元)': round(capital, 2)
            })
            year = entry_date.year
            yearly_lots[year] = yearly_lots.get(year, 0) + lots
            
            # 更新最後一筆資金記錄
            capital_history[-1] = capital

    trades_df = pd.DataFrame(trades)

    # ===== 樣式處理 =====
    def highlight_direction(row):
        color = 'background-color: #fddddd' if row['方向'] == '多' else 'background-color: #d4f4dd'
        return [color if col == '方向' else '' for col in row.index]

    def highlight_profit(row):
        return ['color: red' if col == '損益金額(元)' and row['損益金額(元)'] < 0 else '' for col in row.index]

    st.subheader("📋 交易明細表")
    st.dataframe(trades_df.style.apply(highlight_direction, axis=1).apply(highlight_profit, axis=1),
                 use_container_width=True)

    # ===== 回測設定摘要 =====
    st.subheader("📋 回測設定")
    st.markdown(f"""
    - 策略模式：**{strategy_mode}**
    - 均線設定：**{moving_avg_days}日線**
    - 口數模式：**{lot_mode}**
    - 每點價值：**{point_value}元**
    - 固定口數槓桿：**{leverage}倍**
    - 動態口數槓桿：**{dynamic_leverage}倍**
    - 回測區間：**{start_year if start_year != '全部' else '最早'} ➜ {end_year if end_year != '全部' else '最晚'}**
    - 初始資金：**{start_capital:,.0f} 元**
    - 每月定期投入金額：**{monthly_invest:,.0f} 元**
    - 是否計入交易成本：**{'是' if use_fee else '否'}**
    - 每口交易成本（買/賣）：**{buy_fee}/{sell_fee} 元**
    """)

    # ===== 資金 vs 大盤曲線 =====
    if capital_date:
        st.subheader("📈 資金成長曲線 vs 大盤指數")
        fig, ax1 = plt.subplots(figsize=(14, 6))
        ax1.plot(capital_date, capital_history, color='blue', label='資金成長')
        ax1.set_ylabel("資金", color='blue')
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
        ax2 = ax1.twinx()
        ax2.plot(capital_date, index_history, color='green', linestyle='--', label='大盤指數')
        ax2.set_ylabel("大盤", color='green')
        fig.legend(loc="upper left")
        ax1.grid(True)
        st.pyplot(fig)

    # ===== 年報酬率 =====
    st.subheader("📅 每年年化報酬率")
    df_capital = pd.DataFrame({'日期': capital_date, '資金': capital_history})
    df_capital['年份'] = pd.to_datetime(df_capital['日期']).dt.year
    yearly = df_capital.groupby('年份').agg({'資金': ['first', 'last']})
    yearly.columns = ['期初資金', '期末資金']
    yearly['年化報酬率 (%)'] = (yearly['期末資金'] / yearly['期初資金'] - 1) * 100
    st.dataframe(
        yearly.fillna(0).style.format({'期初資金': '{:,.0f}', '期末資金': '{:,.0f}', '年化報酬率 (%)': '{:.2f}%'}))

    # ===== 每年最大回撤率 (MDD) 表格 =====
    st.subheader("📉 每年最大回撤率（MDD）")
    if not df_capital.empty:
        df_capital['年份'] = pd.to_datetime(df_capital['日期']).dt.year
        yearly_mdd_list = []
        for year, group in df_capital.groupby('年份'):
            values = group['資金'].values
            # 計算最大回撤率
            if len(values) < 2:
                mdd = 0
            else:
                cummax = np.maximum.accumulate(values)
                # 確保分母非零
                drawdowns = 1 - values / np.where(cummax != 0, cummax, 1) 
                mdd = np.max(drawdowns)
            yearly_mdd_list.append({'年份': year, '最大回撤率 (%)': round(mdd * 100, 2)})
        mdd_df = pd.DataFrame(yearly_mdd_list)
        st.dataframe(mdd_df, use_container_width=True)
    else:
        st.info("無法計算每年最大回撤率，因資金資料不足。")

    # ===== 每年指數漲跌幅（表格與圖表） =====
    st.subheader("📅 每年指數漲跌幅（收盤價）")
    df['年份'] = df['日期'].dt.year
    yearly_index = df.groupby('年份').agg({'收盤價': ['first', 'last']})
    yearly_index.columns = ['年初收盤', '年末收盤']
    yearly_index['指數漲跌幅 (%)'] = (yearly_index['年末收盤'] / yearly_index['年初收盤'] - 1) * 100
    st.dataframe(yearly_index.style.format({
        '年初收盤': '{:,.2f}', '年末收盤': '{:,.2f}', '指數漲跌幅 (%)': '{:.2f}%'
    }))

    # 繪製每年指數漲跌幅圖表
    fig_y, ax_y = plt.subplots(figsize=(10, 4))
    ax_y.bar(yearly_index.index.astype(str), yearly_index['指數漲跌幅 (%)'], color=['#f44336' if x < 0 else '#2196f3' for x in yearly_index['指數漲跌幅 (%)']])
    ax_y.axhline(0, color='black', linewidth=1)
    ax_y.set_xlabel("年份")
    ax_y.set_ylabel("指數漲跌幅 (%)")
    ax_y.set_title("每年指數漲跌幅（收盤價）")
    for i, v in enumerate(yearly_index['指數漲跌幅 (%)']):
        ax_y.text(i, v, f"{v:.1f}%", color="black", ha="center", va="bottom" if v>=0 else "top", fontsize=9)
    st.pyplot(fig_y)

    # ===== 每月指數漲跌幅（表格與圖表） =====
    st.subheader("📊 每月指數漲跌幅（收盤價）")
    df['月份'] = df['日期'].dt.to_period('M')
    monthly_index = df.groupby('月份').agg({'收盤價': ['first', 'last']})
    monthly_index.columns = ['月初收盤', '月末收盤']
    monthly_index['指數漲跌幅 (%)'] = (monthly_index['月末收盤'] / monthly_index['月初收盤'] - 1) * 100
    st.dataframe(monthly_index.reset_index().style.format({
        '月初收盤': '{:,.2f}', '月末收盤': '{:,.2f}', '指數漲跌幅 (%)': '{:.2f}%'
    }))

    # 繪製每月指數漲跌幅圖表
    fig_m, ax_m = plt.subplots(figsize=(14, 4))
    month_labels = monthly_index.index.astype(str)
    ax_m.bar(month_labels, monthly_index['指數漲跌幅 (%)'], color=['#f44336' if x < 0 else '#4caf50' for x in monthly_index['指數漲跌幅 (%)']])
    ax_m.axhline(0, color='black', linewidth=1)
    ax_m.set_xlabel("月份")
    ax_m.set_ylabel("指數漲跌幅 (%)")
    ax_m.set_title("每月指數漲跌幅（收盤價）")
    show_xticks = [i for i in range(0, len(month_labels), max(1, len(month_labels)//16))]
    ax_m.set_xticks(show_xticks)
    ax_m.set_xticklabels([month_labels[i] for i in show_xticks], rotation=45)
    st.pyplot(fig_m)

    # ===== 每月漲跌幅分布統計 =====
    st.subheader("📊 每月指數漲跌幅分布統計（1%、2%、3%...）")
    bins = list(range(-20, 22))  # -20% ~ 21%
    labels = [f"{i}%" for i in bins[:-1]]
    monthly_index['漲跌幅桶'] = pd.cut(
        monthly_index['指數漲跌幅 (%)'], bins=bins, right=False, labels=labels
    )
    bucket_counts = monthly_index['漲跌幅桶'].value_counts().sort_index()
    total_months = len(monthly_index)
    bucket_pct = (bucket_counts / total_months * 100).round(2)
    result_df = pd.DataFrame({
        '區間': bucket_counts.index,
        '次數': bucket_counts.values,
        '百分比(%)': bucket_pct.values
    })
    result_df = result_df[result_df['次數'] > 0]
    st.dataframe(result_df, use_container_width=True)
    # 長條圖
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(result_df['區間'], result_df['次數'], color=['#f44336' if '-' in str(x) else '#4caf50' for x in result_df['區間']])
    ax.set_xlabel("每月漲跌幅區間")
    ax.set_ylabel("次數")
    ax.set_title("每月指數漲跌幅分布")
    for i, v in enumerate(result_df['次數']):
        if v > 0:
            ax.text(i, v, str(v), ha='center', va='bottom', fontsize=8)
    st.pyplot(fig)
    # 百分比圖
    fig2, ax2 = plt.subplots(figsize=(12, 4))
    ax2.bar(result_df['區間'], result_df['百分比(%)'], color=['#f44336' if '-' in str(x) else '#4caf50' for x in result_df['區間']])
    ax2.set_xlabel("每月漲跌幅區間")
    ax2.set_ylabel("百分比(%)")
    ax2.set_title("每月指數漲跌幅分布（百分比）")
    for i, v in enumerate(result_df['百分比(%)']):
        if v > 0:
            ax2.text(i, v, f"{v:.1f}%", ha='center', va='bottom', fontsize=8)
    st.pyplot(fig2)

    # ===== 績效統計分析 (已修改：新增獲利/虧損次數、平均金額、風險報酬比、自選指標) =====
    st.subheader("📊 績效統計分析")
    if not trades_df.empty:
        # **【計算邏輯】**
        winning_trades = trades_df[trades_df['損益金額(元)'] > 0]
        losing_trades = trades_df[trades_df['損益金額(元)'] <= 0]
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        avg_profit = winning_trades['損益金額(元)'].mean() if num_wins > 0 else 0
        avg_loss = losing_trades['損益金額(元)'].mean() if num_losses > 0 else 0
        risk_reward_ratio = -avg_profit / avg_loss if avg_loss < 0 and avg_profit > 0 else np.nan
        win_rate = (trades_df['損益金額(元)'] > 0).mean() * 100
        peak = capital_history[0]
        max_dd_value = 0
        mdd_start = mdd_end = capital_date[0]
        temp_start = capital_date[0]
        for i in range(len(capital_history)):
            if capital_history[i] > peak:
                peak = capital_history[i]
                temp_start = capital_date[i]
            dd = capital_history[i] - peak
            if dd < max_dd_value:
                max_dd_value = dd
                mdd_start = temp_start
                mdd_end = capital_date[i]
        trades_df['報酬率 (%)'] = trades_df['損益金額(元)'] / (
                        trades_df['進場價'] * trades_df['交易口數'] * point_value) * 100
        max_gain_pct = trades_df['報酬率 (%)'].max()
        max_loss_pct = trades_df['報酬率 (%)'].min()
        total_days = trades_df['持有天數'].sum()
        
        # **【修改展示排版 - 根據自選指標動態顯示】**
        st.markdown('#### 績效指標')

        # 將所有計算結果整合到一個字典中
        metrics_values = {
            "num_trades": (f"{len(trades_df):,}", "總交易次數", None),
            "win_rate": (f"{win_rate:.2f}%", "勝率 (%)", None),
            "num_wins": (f"{num_wins:,} 次", "獲利次數", None),
            "num_losses": (f"{num_losses:,} 次", "虧損次數", None),
            "avg_profit": (f"{avg_profit:,.0f} 元", "平均獲利金額", None),
            "avg_loss": (f"{-avg_loss:,.0f} 元", "平均虧損金額", 'inverse'), # 使用絕對值
            "risk_reward_ratio": (f"{risk_reward_ratio:.2f} : 1" if not np.isnan(risk_reward_ratio) else "N/A", "風險報酬比 (R/R)", None),
            "max_dd_value": (f"{int(max_dd_value):,} 元", "最大虧損 (MDD)", 'inverse'),
            "max_gain_pct": (f"{max_gain_pct:.2f} %", "最大單筆報酬率", None),
            "max_loss_pct": (f"{max_loss_pct:.2f} %", "最大單筆虧損率", 'inverse'),
            "total_days": (f"{total_days:,} 天", "總交易持有天數", None),
        }
        
        # 根據 selected_metrics_map 篩選並排序要顯示的指標
        display_metrics = []
        for key_internal, key_display in selected_metrics_map.items():
            if key_internal in metrics_values:
                display_metrics.append((key_display, *metrics_values[key_internal]))
                
        # 動態創建欄位並顯示指標 (每排最多 4 個)
        for i in range(0, len(display_metrics), 4):
            cols = st.columns(min(4, len(display_metrics) - i))
            for j, metric_data in enumerate(display_metrics[i:i+4]):
                title, value, delta_color = metric_data[0], metric_data[1], metric_data[2]
                if title == "平均虧損金額": # 特別處理 Help text
                    cols[j].metric(title, value, delta_color=delta_color, help="此為虧損的絕對值")
                elif title == "風險報酬比 (R/R)": # 特別處理 Help text
                    cols[j].metric(title, value, delta_color=delta_color, help="平均獲利金額 / 平均虧損金額的絕對值")
                else:
                    cols[j].metric(title, value, delta_color=delta_color)

        # 最大回撤期間 (保持固定顯示)
        st.markdown("---")
        st.markdown(f"""
        **🔻 最大回撤期間：**
        - 起始日期：**{mdd_start.strftime('%Y-%m-%d')}**
        - 結束日期：**{mdd_end.strftime('%Y-%m-%d')}**
        """)
        
        # 總資產與累積報酬率 (保持原樣)
        st.subheader("💰 總資產與累積報酬率")
        final_capital = capital_history[-1] if capital_history else start_capital
        total_return = (final_capital - start_capital) / start_capital * 100
        col1, col2 = st.columns(2)
        col1.metric("回測結束資產", f"{final_capital:,.0f} 元")
        col2.metric("累積報酬率", f"{total_return:.2f} %")
        
        # 每年總交易口數 (保持原樣)
        st.subheader("📊 每年總交易口數")
        if yearly_lots:
            yearly_lots_df = pd.DataFrame(yearly_lots.items(), columns=['年份', '總交易口數'])
            st.dataframe(yearly_lots_df)
        else:
            st.info("沒有交易紀錄，無法顯示每年總交易口數。")

        # 每月報酬統計 (保持原樣)
        st.subheader("📈 每月報酬統計")
        df_capital['月份'] = df_capital['日期'].dt.to_period('M')
        monthly = df_capital.groupby('月份').agg({'資金': ['first', 'last']})
        monthly.columns = ['期初資金', '期末資金']
        monthly['月報酬率 (%)'] = (monthly['期末資金'] / monthly['期初資金'] - 1) * 100
        st.dataframe(monthly.reset_index().style.format({
            '期初資金': '{:,.0f}', '期末資金': '{:,.0f}', '月報酬率 (%)': '{:.2f}%'
        }))

    # ===== Monte Carlo 模擬 =====
    if do_mc and len(capital_history) > 2:
        st.subheader("🔀 Monte Carlo 模擬資產路徑")
        np.random.seed(mc_seed)
        capital_arr = np.array(capital_history)
        returns = capital_arr[1:] / capital_arr[:-1] - 1  # 策略日報酬率
        sim_days = len(returns)
        sim_rounds = mc_sim_round
        sim_results = []
        for _ in range(sim_rounds):
            rand_returns = np.random.choice(returns, sim_days, replace=True)
            path = start_capital * np.cumprod(1 + rand_returns)
            sim_results.append(path)
        sim_results = np.array(sim_results)
        # 畫出部分模擬路徑
        fig, ax = plt.subplots(figsize=(14, 6))
        for i in range(min(50, sim_results.shape[0])):
            ax.plot(sim_results[i], color='grey', alpha=0.2)
        ax.plot(capital_arr, color='blue', linewidth=2, label='實際資金曲線')
        ax.set_title("Monte Carlo資產模擬（灰色線為隨機路徑，藍色為實際）")
        ax.set_ylabel("資產（元）")
        ax.set_xlabel("天數")
        ax.legend()
        st.pyplot(fig)
        # 【註解 1 - 已加回】
        st.caption("Monte Carlo 模擬路徑圖：灰色線為根據歷史日報酬率隨機生成的潛在資產路徑，藍色線為策略的實際資金曲線。")

        # 百分位區間過濾 + 分箱
        final_assets = sim_results[:, -1]
        lower = np.percentile(final_assets, remove_low_pct)
        upper = np.percentile(final_assets, 100 - remove_high_pct)
        mask = (final_assets >= lower) & (final_assets <= upper)
        filtered_assets = final_assets[mask]
        min_asset = int(np.floor(filtered_assets.min()))
        max_asset = int(np.ceil(filtered_assets.max()))
        bins = np.linspace(min_asset, max_asset, 11, dtype=int)
        counts, edges = np.histogram(filtered_assets, bins=bins)

        fig2, ax2 = plt.subplots(figsize=(10, 4))
        bars = ax2.hist(filtered_assets, bins=edges, color='skyblue', alpha=0.85, rwidth=0.9)
        ax2.set_title(f"Monte Carlo最終資產分布（去除前{remove_low_pct}%與後{remove_high_pct}%）")
        ax2.set_xlabel("最終資產（元）")
        ax2.set_ylabel("次數")
        ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
        for i in range(len(counts)):
            x_pos = (edges[i] + edges[i+1]) / 2
            y_pos = counts[i]
            if y_pos > 0:
                ax2.text(x_pos, y_pos, str(counts[i]), ha='center', va='bottom', fontsize=9)
        st.pyplot(fig2)
        # 【註解 2 - 已加回】
        st.caption(f"經過 Monte Carlo 模擬後，最終資產的頻率分佈圖，並已去除前 {remove_low_pct}% 最低值與後 {remove_high_pct}% 最高值，以提供更具參考性的區間預測。")

        hist_df = pd.DataFrame({
            '資產下界': edges[:-1],
            '資產上界': edges[1:],
            '次數': counts
        })
        hist_df = hist_df[hist_df['次數'] > 0]
        hist_df['資產區間'] = hist_df.apply(lambda r: f"{int(r['資產下界']):,} ~ {int(r['資產上界']):,}", axis=1)
        hist_df = hist_df[['資產區間', '次數']]
        st.dataframe(hist_df, use_container_width=True)

else:
    st.info("👆 請上傳加權指數Excel檔案或將檔案置於專案目錄，並檢查檔名是否為 `加權指數資料.xlsx`。")
