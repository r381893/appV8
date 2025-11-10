import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

# 確保中文字體顯示正常
plt.rcParams['font.family'] = 'Microsoft JhengHei'

# ====================================
# CSS 注入函式 (保持不變)
# ====================================
def inject_custom_css():
    """將美化所需的 CSS 程式碼直接注入到 Streamlit 頁面，確保樣式生效且框框樣式加強。"""
    
    # 內嵌核心 CSS 內容
    embedded_css = """
        /* 應用程式主體與側邊欄基礎樣式 */
        body { font-family: 'Microsoft JhengHei', sans-serif; }

        /* 隱藏 Streamlit 預設的右上角選單和 Footer */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }

        /* ========================================================= */
        /* 卡片樣式 (data-card) - 帶來邊框、圓角和陰影的框框效果 (已強化) */
        /* ========================================================= */
        .data-card {
            border: 2px solid #cccccc; /* 邊框加粗並變深 */
            border-radius: 12px; /* 圓角更明顯 */
            padding: 20px;
            margin-bottom: 25px; /* 增加卡片間距 */
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12); /* 陰影加深 */
            background-color: #ffffff; /* 確保白色背景 */
        }

        /* 卡片標題樣式 (card-header) */
        .card-header {
            font-size: 1.6em;
            font-weight: bold;
            color: #2c3e50;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db; /* 使用醒目的藍色底線 */
            margin-bottom: 18px !important;
            display: flex; /* 確保圖標和文字對齊 */
            align-items: center;
        }

        .card-header span {
            margin-right: 12px;
            color: #3498db; /* 藍色強調色 */
            font-size: 1.1em; /* 讓圖標稍微大一點 */
        }

        /* ========================================================= */
        /* 進度條/統計條樣式 (針對卡片 4 的自訂 HTML) */
        /* ========================================================= */
        .bar-container { margin-bottom: 15px; }
        .bar-label {
            display: flex;
            justify-content: space-between;
            font-size: 0.9em;
            font-weight: bold;
            color: #34495e;
            margin-bottom: 5px;
        }
        .progress-bar {
            background-color: #e9ecef;
            border-radius: 6px;
            height: 12px;
            overflow: hidden;
        }

        /* Streamlit 內建元素的調整 */
        .stAlert { border-radius: 8px; font-size: 1em; }
        [data-testid="stMetric"] { padding: 5px !important; }
        [data-testid="stMetricLabel"] { font-size: 1em; font-weight: bold; color: #5c6773; }
    """
    # 透過 st.markdown 注入 <style> 標籤
    st.markdown(f'<style>{embedded_css}</style>', unsafe_allow_html=True)

# ====================================
# Streamlit 應用程式主體
# ====================================

st.set_page_config(page_title="台股加權指數回測系統", layout="wide")

# 執行 CSS 注入
inject_custom_css()

st.title("📈 台股加權指數回測系統")

# 【🚨 檔案讀取修改區塊：優先從本地讀取 🚨】
DATA_FILE = '加權指數資料.xlsx'
data_source = None
df = None

# 1. 嘗試從本地目錄讀取（適用於已部署的 App 或本地執行）
if os.path.exists(DATA_FILE):
    st.info(f"從本地文件讀取資料：**{DATA_FILE}** (無需上傳)")
    try:
        df = pd.read_excel(DATA_FILE)
        data_source = DATA_FILE
    except Exception as e:
        st.error(f"讀取 {DATA_FILE} 失敗，錯誤訊息: {e}")
        df = None
else:
    # 2. 如果本地沒有檔案，則顯示上傳按鈕 (備用)
    uploaded_file = st.file_uploader("請上傳加權指數Excel檔案 (格式：日期, 收盤價)", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        data_source = uploaded_file.name

# 【🚨 程式碼主體：確保 df 成功讀取才執行 🚨】
if data_source and df is not None and not df.empty:
    
    # 檢查並清理 DataFrame
    df.columns = ['日期', '收盤價']
    df['日期'] = pd.to_datetime(df['日期'])
    df = df.sort_values('日期').reset_index(drop=True)

    available_years = sorted(list(set(df['日期'].dt.year)))
    # 確保選單中 '全部' 是第一個選項
    start_year_options = ["全部"] + available_years
    end_year_options = ["全部"] + available_years[::-1]
    
    start_year = st.sidebar.selectbox("選擇回測開始年份", options=start_year_options, index=0)
    end_year = st.sidebar.selectbox("選擇回測結束年份", options=end_year_options, index=0)

    # 修正：只有年份都不是"全部"時才做篩選，且保證型態正確
    if start_year != "全部" and end_year != "全部":
        df = df[(df['日期'].dt.year >= int(start_year)) & (df['日期'].dt.year <= int(end_year))].reset_index(drop=True)

    # ====== 參數設定 (Sidebar) ======
    auto_opt = st.sidebar.checkbox("自動優化均線天數", value=False)
    if auto_opt:
        min_ma = st.sidebar.number_input("均線天數-起始", min_value=2, max_value=500, value=5, step=1)
        max_ma = st.sidebar.number_input("均線天數-結束", min_value=2, max_value=500, value=60, step=1)
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
    # ====== 交易成本設定 (Sidebar) ======
    use_fee = st.sidebar.checkbox("納入交易成本", value=True)
    buy_fee = st.sidebar.number_input("每口買進手續費", value=35, step=1)
    sell_fee = st.sidebar.number_input("每口賣出手續費", value=35, step=1)
    # ====== Monte Carlo 模擬設定 (Sidebar) ======
    do_mc = st.sidebar.checkbox("Monte Carlo 模擬", value=False)
    mc_sim_round = st.sidebar.number_input("Monte Carlo模擬次數", value=500, min_value=100, max_value=2000, step=100)
    mc_seed = st.sidebar.number_input("Monte Carlo隨機種子", value=42, step=1)
    remove_low_pct = st.sidebar.number_input("去除前幾%最低值", min_value=0, max_value=40, value=5, step=1)
    remove_high_pct = st.sidebar.number_input("去除後幾%最高值", min_value=0, max_value=40, value=5, step=1)

    # ====== 參數優化主體 (註釋：用於自動尋找最佳均線天數) ======
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
        
        # 初始資金紀錄 (解決 capital_history 初始為空的問題)
        capital_history.append(capital)
        capital_date.append(df_bt.loc[0, '日期'])
        index_history.append(df_bt.loc[0, '收盤價'])
        
        for i in range(1, len(df_bt)):
            this_month = df_bt.loc[i, '日期'].month
            # 定期投入
            if monthly_invest > 0 and this_month != last_month:
                capital += monthly_invest
            last_month = this_month
            
            # 確保均線數據存在
            if pd.isna(df_bt.loc[i, f'{moving_avg_days}日線']):
                capital_history.append(capital)
                capital_date.append(df_bt.loc[i, '日期'])
                index_history.append(df_bt.loc[i, '收盤價'])
                continue
                
            action = df_bt.loc[i, '收盤價'] - df_bt.loc[i, f'{moving_avg_days}日線']
            current_price = df_bt.loc[i, '收盤價']
            date = df_bt.loc[i, '日期']
            
            # 進場判斷
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
            
            # 出場/換倉判斷
            else:
                # 動態口數計算 (在進場時 entry_price 確定後，口數也確定)
                lots = fixed_lots if lot_mode == "固定口數" else max(
                    int((capital * dynamic_leverage) / (entry_price * point_value)) if entry_price else 0, 0)
                
                # 只做多平倉
                if strategy_mode == "只做多" and action < 0 and position == '多':
                    fee = (buy_fee + sell_fee) * lots if use_fee else 0
                    profit = (current_price - entry_price) * lots * point_value - fee
                    capital += profit
                    trades.append({
                        '進場日期': entry_date, '出場日期': date,
                        '方向': position, '持有天數': (date - entry_date).days,
                        '進場價': entry_price, '出場價': current_price,
                        '交易口數': lots, '交易成本(元)': fee,
                        '損益金額(元)': round(profit, 2),
                        '累積資金(元)': round(capital, 2)
                    })
                    # 重設狀態
                    holding = False
                    position = None
                    entry_price = None
                    entry_date = None

                # 只做空平倉
                elif strategy_mode == "只做空" and action > 0 and position == '空':
                    fee = (buy_fee + sell_fee) * lots if use_fee else 0
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
                    # 重設狀態
                    holding = False
                    position = None
                    entry_price = None
                    entry_date = None

                # 雙向換倉
                elif strategy_mode == "雙向：站上多、跌破空":
                    if position == '多' and action < 0: # 多單平倉 + 開空單
                        fee = (buy_fee + sell_fee) * lots if use_fee else 0
                        profit = (current_price - entry_price) * lots * point_value - fee
                        capital += profit
                        trades.append({
                            '進場日期': entry_date, '出場日期': date,
                            '方向': position, '持有天數': (date - entry_date).days,
                            '進場價': entry_price, '出場價': current_price,
                            '交易口數': lots, '交易成本(元)': fee,
                            '損益金額(元)': round(profit, 2),
                            '累積資金(元)': round(capital, 2)
                        })
                        
                        # 開空單
                        holding = True
                        position = '空'
                        entry_price = current_price
                        entry_date = date
                        
                    elif position == '空' and action > 0: # 空單平倉 + 開多單
                        fee = (buy_fee + sell_fee) * lots if use_fee else 0
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
                        
                        # 開多單
                        holding = True
                        position = '多'
                        entry_price = current_price
                        entry_date = date
                        
            capital_history.append(capital)
            capital_date.append(date)
            index_history.append(current_price)

        # 確保 capital_history 不是空的，並只返回累積報酬率
        if not capital_history:
             return 0, [], [], []
             
        # 計算總累積報酬率（優化器只關注這個值）
        total_return = (capital_history[-1] - start_capital) / start_capital * 100
        return total_return, capital_history, capital_date, index_history

    # ====== 自動優化均線天數 (卡片 1) ======
    if auto_opt:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.markdown("<h2 class='card-header'><span>🔎</span> 自動優化均線天數</h2>", unsafe_allow_html=True)
        
        results = []
        bar = st.progress(0)
        # 優化迴圈中使用 backtest 函式
        for idx, ma in enumerate(ma_range):
            try:
                r, _, _, _ = backtest(ma)
                results.append({'均線天數': ma, '累積報酬率': r})
            except Exception as e:
                results.append({'均線天數': ma, '累積報酬率': np.nan}) 
            bar.progress((idx+1)/len(ma_range))
        bar.empty()
        
        results_df = pd.DataFrame(results).dropna()
        if not results_df.empty:
            best_row = results_df.loc[results_df['累積報酬率'].idxmax()]
            st.success(f"最佳均線天數：{int(best_row['均線天數'])}，累積報酬率：{best_row['累積報酬率']:.2f}%")
            
            fig_opt, ax_opt = plt.subplots(figsize=(10,4))
            ax_opt.plot(results_df['均線天數'], results_df['累積報酬率'])
            ax_opt.set_xlabel("均線天數")
            ax_opt.set_ylabel("累積報酬率(%)")
            ax_opt.set_title("不同均線天數累積報酬率")
            st.pyplot(fig_opt)
            st.caption("不同均線天數（X軸）對應的策略累積報酬率（Y軸），用於找出最佳均線參數。")
            
            st.dataframe(results_df.style.format({'累積報酬率': '{:.2f}'}), use_container_width=True)
            moving_avg_days = int(best_row['均線天數'])
            st.info(f"後續回測與模擬將自動採用「最佳均線天數」：{moving_avg_days}日線")
        else:
            st.warning("自動優化失敗或無有效數據，請檢查參數設定。")
            moving_avg_days = max(min_ma, 13) # 設置一個安全預設值
            st.info(f"將使用預設均線天數：{moving_avg_days}日線")

        st.markdown("</div>", unsafe_allow_html=True)
        
    # 如果是非優化模式，直接使用設定的 moving_avg_days
    if moving_avg_days is not None:
        df[f'{moving_avg_days}日線'] = df['收盤價'].rolling(window=moving_avg_days).mean()
    else:
        st.error("均線天數未設定，請檢查側邊欄。")
        st.stop() # 停止執行以避免後續錯誤


    # ===== 最新市場判斷 (卡片 2) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>🔍</span> 最新市場判斷</h2>", unsafe_allow_html=True)
    
    latest_price = df.iloc[-1]['收盤價']
    latest_date_str = df.iloc[-1]['日期'].strftime('%Y-%m-%d')
    latest_ma = df.iloc[-1][f'{moving_avg_days}日線']
    
    if not pd.isna(latest_ma):
        st.markdown(f"""
            - 最新日期：**{latest_date_str}**
            - 最新收盤價：**{latest_price:,.2f}**
            - 最新 {moving_avg_days} 日線：**{latest_ma:.2f}**
            """)
        diff = latest_price - latest_ma
        if latest_price > latest_ma:
            st.success(f"📈 現在收盤價高於 {moving_avg_days} 日線 ({diff:.2f}) ➜ **建議：做多**")
        else:
            st.error(f"📉 現在收盤價低於 {moving_avg_days} 日線 ({diff:.2f}) ➜ **建議：做空**")
    else:
        st.warning("均線數據不足，無法進行最新市場判斷。")
        
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 多空建議趨勢圖 (卡片 3) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📊</span> 近 100 日多空建議趨勢圖</h2>", unsafe_allow_html=True)
    
    if len(df) >= 100:
        recent_df = df.iloc[-100:].copy()
        # 確保均線數據存在
        if not pd.isna(recent_df[f'{moving_avg_days}日線']).all():
            recent_df['建議方向'] = recent_df.apply(
                lambda row: 1 if row['收盤價'] > row[f'{moving_avg_days}日線'] else -1, axis=1
            )
            recent_df['簡化日期'] = recent_df['日期'].dt.strftime('%m-%d')
            fig, ax = plt.subplots(figsize=(16, 4))
            ax.bar(
                recent_df['簡化日期'],
                recent_df['建議方向'],
                color=recent_df['建議方向'].map({1: '#ffb6c1', -1: '#90ee90'})
            )
            ax.axhline(0, color='black', linewidth=1)
            ax.set_ylabel('建議方向')
            ax.set_title('近 100 日每日多空建議（1=做多, -1=做空）')
            # 確保 x 軸標籤不擁擠
            x_labels = recent_df['簡化日期'].iloc[::10]
            ax.set_xticks(range(0, 100, 10))
            ax.set_xticklabels(x_labels, rotation=45)
            st.pyplot(fig)
            st.caption("近 100 個交易日，收盤價與移動平均線的相對關係所給出的多空建議（1代表多頭，-1代表空頭）。")
        else:
            st.warning("均線數據不足或有大量缺失值，無法繪製趨勢圖。")
    else:
        st.warning("資料不足 100 天，無法繪製圖表。")
        
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 多空建議統計條 (卡片 4) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📊</span> 近 100 日建議方向統計</h2>", unsafe_allow_html=True)
    
    # 確保 recent_df 存在且均線數據存在
    if 'recent_df' in locals() and len(df) >= 100 and not pd.isna(recent_df[f'{moving_avg_days}日線']).all():
        long_days = (recent_df['建議方向'] == 1).sum()
        short_days = (recent_df['建議方向'] == -1).sum()
        total = long_days + short_days
        
        # 使用 style.css 中的 .bar-container 和 .progress-bar 樣式
        if total > 0:
            st.markdown(f"""
            <div class="bar-container">
                <div class="bar-label">
                    <span>建議「做多」天數: {long_days} 天</span>
                    <span>{long_days / total * 100:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div style="width:{long_days / total * 100}%; background-color: #f44336; height: 100%; border-radius: 6px;"></div>
                </div>
            </div>
            <div class="bar-container">
                <div class="bar-label">
                    <span>建議「做空」天數: {short_days} 天</span>
                    <span>{short_days / total * 100:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div style="width:{short_days / total * 100}%; background-color: #cddc39; height: 100%; border-radius: 6px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("近 100 日無有效均線數據進行統計。")
    else:
        st.warning("資料不足 100 天或均線數據缺失，無法統計。")
        
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 回測主邏輯 (在後台運行) ======
    
    # 初始化用於回測的變數
    trades, capital_history, capital_date, index_history = [], [], [], []
    capital = start_capital
    yearly_lots = {}
    
    holding = False
    position = None
    entry_price = None
    entry_date = None
    
    if len(df) > 0:
        # 初始資金紀錄
        capital_history.append(capital)
        capital_date.append(df.iloc[0]['日期'])
        index_history.append(df.iloc[0]['收盤價'])
        last_month = df.iloc[0]['日期'].month
    else:
        st.error("數據檔案沒有任何資料。")
        st.stop()
        

    if strategy_mode == "從頭抱到尾":
        # 僅適用於策略模式為「從頭抱到尾」
        if len(df) > 1:
            entry_price = df.iloc[0]['收盤價']
            entry_date = df.iloc[0]['日期']
            
            # 動態口數計算需確保 entry_price 不為 0
            if entry_price > 0:
                lots = fixed_lots if lot_mode == "固定口數" else max(
                    int((capital * dynamic_leverage) / (entry_price * point_value)), 0)
            else:
                lots = fixed_lots
                
            fee = (buy_fee + sell_fee) * lots if use_fee else 0
            
            # 資金變動軌跡 (計算中間過程的資金變化)
            for i in range(1, len(df)):
                this_month = df.loc[i, '日期'].month
                if monthly_invest > 0 and this_month != last_month:
                    capital += monthly_invest
                last_month = this_month
                
                price = df.loc[i, '收盤價']
                prev_price = df.loc[i - 1, '收盤價']
                
                # 每日未平倉損益反映到資本
                profit = (price - prev_price) * lots * point_value
                capital += profit
                
                capital_history.append(capital)
                capital_date.append(df.loc[i, '日期'])
                index_history.append(price)

            # 處理交易明細，將結果計入最終交易 (視為在最後一天平倉)
            final_profit = (df.iloc[-1]['收盤價'] - entry_price) * lots * point_value - fee
            
            # 由於資金已經每日計算，這裡只記錄交易細節
            trades.append({
                '進場日期': entry_date, '出場日期': df.iloc[-1]['日期'],
                '方向': '多', '持有天數': (df.iloc[-1]['日期'] - entry_date).days,
                '進場價': entry_price, '出場價': df.iloc[-1]['收盤價'],
                '交易口數': lots, '交易成本(元)': fee,
                '損益金額(元)': round(final_profit, 2),
                '累積資金(元)': round(capital, 2)
            })
            
            year = entry_date.year
            yearly_lots[year] = yearly_lots.get(year, 0) + lots
            
        else:
            st.warning("資料不足，無法執行「從頭抱到尾」策略。")
            
    else:
        # 其他均線策略
        for i in range(1, len(df)):
            this_month = df.loc[i, '日期'].month
            # 定期投入
            if monthly_invest > 0 and this_month != last_month:
                capital += monthly_invest
            last_month = this_month
            
            # 如果均線數據缺失，則跳過當日交易判斷
            if pd.isna(df.loc[i, f'{moving_avg_days}日線']):
                capital_history.append(capital)
                capital_date.append(df.loc[i, '日期'])
                index_history.append(df.loc[i, '收盤價'])
                continue
                
            action = df.loc[i, '收盤價'] - df.loc[i, f'{moving_avg_days}日線']
            current_price = df.loc[i, '收盤價']
            date = df.loc[i, '日期']
            
            # 進場判斷
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
            
            # 出場/換倉判斷
            else:
                
                # 動態口數計算 (此處的 lots 是為了計算平倉損益)
                lots = fixed_lots if lot_mode == "固定口數" else max(
                    int((capital * dynamic_leverage) / (entry_price * point_value)) if entry_price else 0, 0)
                
                # 只做多平倉
                if strategy_mode == "只做多" and action < 0 and position == '多':
                    fee = (buy_fee + sell_fee) * lots if use_fee else 0
                    profit = (current_price - entry_price) * lots * point_value - fee
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
                    holding = False
                    position = None
                    entry_price = None
                    entry_date = None
                    
                # 只做空平倉
                elif strategy_mode == "只做空" and action > 0 and position == '空':
                    fee = (buy_fee + sell_fee) * lots if use_fee else 0
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
                    holding = False
                    position = None
                    entry_price = None
                    entry_date = None
                    
                # 雙向換倉
                elif strategy_mode == "雙向：站上多、跌破空":
                    if position == '多' and action < 0: # 多單平倉 + 開空單
                        fee = (buy_fee + sell_fee) * lots if use_fee else 0
                        profit = (current_price - entry_price) * lots * point_value - fee
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
                        
                        holding = True
                        position = '空'
                        entry_price = current_price
                        entry_date = date
                        
                    elif position == '空' and action > 0: # 空單平倉 + 開多單
                        fee = (buy_fee + sell_fee) * lots if use_fee else 0
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
                        
                        holding = True
                        position = '多'
                        entry_price = current_price
                        entry_date = date
            
            # 每日資金與指數紀錄
            capital_history.append(capital)
            capital_date.append(date)
            index_history.append(current_price)

    trades_df = pd.DataFrame(trades)
    
    # 設置即時損益的預設值，即使無持倉，也確保變數存在
    unrealized_profit = 0
    lots = 0
    last_price = df.iloc[-1]['收盤價']
    
    # 如果回測結束仍有部位，將當前部位視為未平倉損益
    if holding and strategy_mode != "從頭抱到尾" and entry_price is not None:
        # 由於在迴圈中 lots 每次都會計算，這裡要重新計算一次最終口數
        lots = fixed_lots if lot_mode == "固定口數" else max(
            int((capital * dynamic_leverage) / (entry_price * point_value)) if entry_price else 0, 0)
        
        # 僅計算出場手續費
        fee_exit = sell_fee * lots if use_fee else 0 
        
        if position == '多':
            unrealized_profit = (last_price - entry_price) * lots * point_value - fee_exit
        else:
            unrealized_profit = (entry_price - last_price) * lots * point_value - fee_exit
        
        # 將未平倉損益反映到最終資金上 (僅在最後一個點)
        if capital_history:
            # 為了簡化，我們直接在最後一個點做調整，確保總結數據正確
            capital_history[-1] += unrealized_profit
            capital += unrealized_profit # 更新 capital 總值
            
    # ===== 樣式處理 (後台函式) ======
    def highlight_direction(row):
        color = 'background-color: #fddddd' if row['方向'] == '多' else 'background-color: #d4f4dd'
        return [color if col == '方向' else '' for col in row.index]

    def highlight_profit(row):
        return ['color: red' if col == '損益金額(元)' and row['損益金額(元)'] < 0 else '' for col in row.index]

    # ===== 交易明細表 (卡片 5) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📋</span> 交易明細表</h2>", unsafe_allow_html=True)
    
    if not trades_df.empty:
        st.dataframe(trades_df.style.apply(highlight_direction, axis=1).apply(highlight_profit, axis=1),
                     use_container_width=True)
    else:
        st.info("無交易紀錄。")
                 
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 回測設定摘要 (卡片 6) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📋</span> 回測設定</h2>", unsafe_allow_html=True)
    
    st.markdown(f"""
    - 策略模式：**{strategy_mode}**
    - 均線設定：**{moving_avg_days}日線**
    - 口數模式：**{lot_mode}**
    - 每點價值：**{point_value}元**
    - 固定口數槓桿：**{leverage}倍**
    - 動態口數槓桿：**{dynamic_leverage}倍**
    - 回測區間：**{start_year if start_year != '全部' else '最早'} ➔ {end_year if end_year != '全部' else '最晚'}**
    - 初始資金：**{start_capital:,.0f} 元**
    - 每月定期投入金額：**{monthly_invest:,.0f} 元**
    - 是否計入交易成本：**{'是' if use_fee else '否'}**
    - 每口交易成本（買/賣）：**{buy_fee}/{sell_fee} 元**
    """)
    
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 資金 vs 大盤曲線 (卡片 7) ======
    if capital_date and capital_history:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.markdown("<h2 class='card-header'><span>📈</span> 資金成長曲線 vs 大盤指數</h2>", unsafe_allow_html=True)
        
        # 繪圖前，確保 capital_history 長度一致
        if len(capital_date) == len(capital_history) and len(capital_date) == len(index_history):
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
            st.caption("藍線代表回測期間的資金變化曲線，綠色虛線代表台股大盤指數走勢，用於比較策略與大盤的表現。")
        else:
            st.warning("資金數據或大盤數據長度不一致，無法繪製圖表。")
        
        st.markdown("</div>", unsafe_allow_html=True)

    # ===== 年報酬率 (卡片 8) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📅</span> 每年年化報酬率</h2>", unsafe_allow_html=True)
    
    if capital_date and capital_history:
        # 確保 capital_history 是 DataFrame
        df_capital = pd.DataFrame({'日期': capital_date, '資金': capital_history})
        df_capital['年份'] = pd.to_datetime(df_capital['日期']).dt.year
        yearly = df_capital.groupby('年份').agg({'資金': ['first', 'last']})
        yearly.columns = ['期初資金', '期末資金']
        yearly['年化報酬率 (%)'] = (yearly['期末資金'] / yearly['期初資金'] - 1) * 100
        st.dataframe(
            yearly.fillna(0).style.format({'期初資金': '{:,.0f}', '期末資金': '{:,.0f}', '年化報酬率 (%)': '{:.2f}%'}))
    else:
        st.info("沒有足夠的資金數據計算年報酬率。")
        
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 每年最大回撤率 (MDD) 表格 (卡片 9) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📉</span> 每年最大回撤率（MDD）</h2>", unsafe_allow_html=True)
    
    # 確保 df_capital 存在且有資料
    if 'df_capital' in locals() and not df_capital.empty:
        df_capital['年份'] = pd.to_datetime(df_capital['日期']).dt.year
        yearly_mdd_list = []
        for year, group in df_capital.groupby('年份'):
            values = group['資金'].values
            if len(values) < 2:
                mdd = 0
            else:
                # 累積高點
                cummax = np.maximum.accumulate(values)
                # 回撤率
                drawdowns = 1 - values / cummax
                # 每年最大回撤率 (比率)
                mdd = np.max(drawdowns) 
            yearly_mdd_list.append({'年份': year, '最大回撤率 (%)': round(mdd * 100, 2)})
        mdd_df = pd.DataFrame(yearly_mdd_list)
        st.dataframe(mdd_df, use_container_width=True)
        st.caption("表格顯示的是**各年度內**，資金從年度最高點跌落到最低點的最大百分比損失。")
    else:
        st.info("無法計算每年最大回撤率，因資金資料不足。")
        
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 每年指數漲跌幅（表格與圖表）(卡片 10) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📅</span> 每年指數漲跌幅（收盤價）</h2>", unsafe_allow_html=True)
    
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
    st.caption("各年份（X軸）的台股加權指數年度漲跌幅（Y軸），藍色代表上漲，紅色代表下跌。")
    
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 每月指數漲跌幅（表格與圖表）(卡片 11) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📊</span> 每月指數漲跌幅（收盤價）</h2>", unsafe_allow_html=True)
    
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
    # 智慧設定 x 軸標籤間隔，防止過於擁擠
    show_xticks = [i for i in range(0, len(month_labels), max(1, len(month_labels)//16))]
    ax_m.set_xticks(show_xticks)
    ax_m.set_xticklabels([month_labels[i] for i in show_xticks], rotation=45)
    # 僅標註部分數據，防止擁擠
    for i, v in enumerate(monthly_index['指數漲跌幅 (%)']):
        if i in show_xticks:
            ax_m.text(i, v, f"{v:.2f}%", color="black", ha="center", va="bottom" if v>=0 else "top", fontsize=8)
    st.pyplot(fig_m)
    st.caption("所有月份（X軸）的台股加權指數月度漲跌幅（Y軸），綠色代表上漲，紅色代表下跌。")
    
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 每月漲跌幅分布統計 (卡片 12) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📊</span> 每月指數漲跌幅分布統計（1%、2%、3%...）</h2>", unsafe_allow_html=True)
    
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
    # 使用包含正負號的區間名稱來決定顏色
    ax.bar(result_df['區間'], result_df['次數'], color=['#f44336' if '-' in str(x) else '#4caf50' for x in result_df['區間']])
    ax.axhline(0, color='black', linewidth=1)
    ax.set_xlabel("每月漲跌幅區間")
    ax.set_ylabel("次數")
    ax.set_title("每月指數漲跌幅分布")
    for i, v in enumerate(result_df['次數']):
        if v > 0:
            ax.text(i, v, str(v), ha='center', va='bottom', fontsize=8)
    st.pyplot(fig)
    st.caption("將每月指數漲跌幅（X軸）以 1% 為區間進行分組，顯示各區間發生的次數（Y軸）。")
    
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
    st.caption("將每月指數漲跌幅（X軸）以 1% 為區間進行分組，顯示各區間發生的機率百分比（Y軸）。")
    
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 績效統計分析 (卡片 13) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📊</span> 績效統計分析</h2>", unsafe_allow_html=True)
    
    if not trades_df.empty:
        # 勝率：獲利交易次數佔總交易次數的百分比
        win_rate = (trades_df['損益金額(元)'] > 0).mean() * 100 
        
        # --- 最大回撤 (MDD) 計算 ---
        if capital_history:
            capital_arr_mdd = np.array(capital_history)
            
            # 累積高點：找出從開始到每一天為止資金的最高點
            peak_mdd = np.maximum.accumulate(capital_arr_mdd) 
            
            # 回撤率： (累積高點 - 當前資金) / 累積高點
            drawdowns_mdd = 1 - capital_arr_mdd / peak_mdd
            
            # 最大回撤率 (比率)：整個回測期間最大的回撤百分比
            max_dd_ratio = np.max(drawdowns_mdd)
            
            # 計算最大回撤的金額
            peak_value = np.max(peak_mdd) # 歷史資金最高峰
            # 資金谷底：發生最大回撤時的資金最低點
            trough_value = capital_arr_mdd[np.argmax(drawdowns_mdd)] 
            # 最大回撤金額：歷史高點 - 谷底資金
            max_dd_value = trough_value - peak_value
            
        else:
            max_dd_value = 0
            max_dd_ratio = 0.0
            
        # 計算最大單筆報酬率和虧損率
        trades_df['報酬率 (%)'] = trades_df['損益金額(元)'] / (
            trades_df['進場價'] * trades_df['交易口數'] * point_value) * 100
        
        max_gain_pct = trades_df['報酬率 (%)'].max()
        max_loss_pct = trades_df['報酬率 (%)'].min()
        total_days = trades_df['持有天數'].sum()
        
        # --- 顯示核心績效指標 ---
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("總交易次數", f"{len(trades_df):,}")
        col2.metric("勝率 (%)", f"{win_rate:.2f}%")
        col3.metric("最大虧損 (MDD)", f"{max_dd_value:,.0f} 元") # 顯示 MDD 的金額
        col4.metric("最大單筆報酬率", f"{max_gain_pct:.2f} %")
        col5.metric("最大單筆虧損率", f"{max_loss_pct:.2f} %")
        col6.metric("總交易持有天數", f"{total_days:,} 天")
        
        # MDD 期間的提示
        if capital_history:
             # 【此處是總體最大回撤率比率】
             st.markdown(f"**🔻 最大回撤率 (比率)：** **{max_dd_ratio * 100:.2f} %**") 
             st.caption("此數值為**整個回測期間**，資金從歷史最高峰跌落到谷底的最大百分比損失。")


        # 【即時損益狀態顯示】
        st.markdown("### 💡 即時損益")
        
        if holding and strategy_mode != "從頭抱到尾" and entry_price is not None:
            # 確保 last_price, lots, unrealized_profit 變數已在上方更新
            st.success(
                f"目前持倉：{position}單 {lots} 口，進場價 {entry_price:,.2f} ➔ 最新價 {last_price:,.2f}，**即時損益：{unrealized_profit:,.0f} 元**（已反映在最終資金中）")
        else:
            st.info("目前無持倉，無即時損益。")
            
        st.markdown("### 💰 總資產與累積報酬率")
        final_capital = capital_history[-1] if capital_history else start_capital
        total_return = (final_capital - start_capital) / start_capital * 100
        col1, col2 = st.columns(2)
        col1.metric("回測結束資產", f"{final_capital:,.0f} 元")
        col2.metric("累積報酬率", f"{total_return:.2f} %")
        
        st.markdown("### 📊 每年總交易口數")
        if yearly_lots:
            yearly_lots_df = pd.DataFrame(yearly_lots.items(), columns=['年份', '總交易口數'])
            st.dataframe(yearly_lots_df)
        else:
            st.info("沒有交易紀錄，無法顯示每年總交易口數。")
            
    else:
        st.info("沒有交易紀錄或資金數據，無法進行績效分析。")
        
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== 每月報酬統計 (卡片 14) ======
    st.markdown("<div class='data-card'>", unsafe_allow_html=True)
    st.markdown("<h2 class='card-header'><span>📈</span> 每月報酬統計</h2>", unsafe_allow_html=True)
    
    # 確保 df_capital 存在且有資料
    if 'df_capital' in locals() and not df_capital.empty:
        df_capital['月份'] = df_capital['日期'].dt.to_period('M')
        monthly = df_capital.groupby('月份').agg({'資金': ['first', 'last']})
        monthly.columns = ['期初資金', '期末資金']
        
        # 這裡使用 '期末資金'
        monthly['月報酬率 (%)'] = (monthly['期末資金'] / monthly['期初資金'] - 1) * 100
        
        st.dataframe(monthly.reset_index().style.format({
            '期初資金': '{:,.0f}', '期末資金': '{:,.0f}', '月報酬率 (%)': '{:.2f}%'
        }))
    else:
        st.info("沒有足夠的資金數據計算月報酬率。")
    
    st.markdown("</div>", unsafe_allow_html=True)

    # ===== Monte Carlo 模擬 (卡片 15) ======
    # 僅在有足夠資金歷史數據時執行
    if do_mc and capital_history and len(capital_history) > 2:
        st.markdown("<div class='data-card'>", unsafe_allow_html=True)
        st.markdown("<h2 class='card-header'><span>🔀</span> Monte Carlo 模擬資產路徑</h2>", unsafe_allow_html=True)
        
        np.random.seed(mc_seed)
        capital_arr = np.array(capital_history)
        
        # 策略日報酬率：避免除以零
        # 修正：確保分母不為零，且日報酬率的長度是 N-1
        capital_arr_safe = capital_arr[:-1].copy()
        capital_arr_safe[capital_arr_safe == 0] = 1 # 避免除以 0，但這情況極少發生
        returns = np.diff(capital_arr) / capital_arr_safe
        
        if len(returns) > 0:
            sim_days = len(returns)
            sim_rounds = mc_sim_round
            sim_results = []
            
            # 使用進度條顯示模擬進度
            mc_bar = st.progress(0)
            for i in range(sim_rounds):
                # 隨機重抽樣歷史報酬率
                rand_returns = np.random.choice(returns, sim_days, replace=True)
                # 計算累積資產路徑 (從 start_capital 開始累積)
                path = start_capital * np.cumprod(1 + rand_returns)
                sim_results.append(path)
                mc_bar.progress((i + 1) / sim_rounds)
            mc_bar.empty()
            
            sim_results = np.array(sim_results)
            
            # 畫出部分模擬路徑
            fig, ax = plt.subplots(figsize=(14, 6))
            for i in range(min(50, sim_results.shape[0])):
                ax.plot(sim_results[i], color='grey', alpha=0.2)
            
            # 實際資金曲線的長度是 N，模擬路徑是 N-1，因此需要調整 X 軸
            ax.plot(range(len(capital_arr)), capital_arr, color='blue', linewidth=2, label='實際資金曲線')
            ax.set_title("Monte Carlo資產模擬（灰色線為隨機路徑，藍色為實際）")
            ax.set_ylabel("資產（元）")
            ax.set_xlabel("天數")
            ax.legend()
            st.pyplot(fig)
            st.caption("圖中藍線為實際回測的資金成長曲線，灰色線為根據歷史日報酬率隨機抽樣模擬出的資產成長路徑，用於評估策略在不同情境下的穩健性。")
    
            # 百分位區間過濾 + 分箱
            final_assets = sim_results[:, -1]
            lower = np.percentile(final_assets, remove_low_pct)
            upper = np.percentile(final_assets, 100 - remove_high_pct)
            mask = (final_assets >= lower) & (final_assets <= upper)
            filtered_assets = final_assets[mask]
            
            # 繪製最終資產分佈圖
            if len(filtered_assets) > 0:
                min_asset = int(np.floor(filtered_assets.min() / 10000) * 10000)
                max_asset = int(np.ceil(filtered_assets.max() / 10000) * 10000)
                # 至少要有兩個 bin 邊界
                bins = np.linspace(min_asset, max_asset, 11, dtype=int) if max_asset > min_asset else np.array([min_asset, min_asset + 10000])

                fig2, ax2 = plt.subplots(figsize=(10, 4))
                counts, edges, bars = ax2.hist(filtered_assets, bins=bins, color='skyblue', alpha=0.85, rwidth=0.9)
                ax2.set_title(f"Monte Carlo最終資產分布（去除前{remove_low_pct}%與後{remove_high_pct}%）")
                ax2.set_xlabel("最終資產（元）")
                ax2.set_ylabel("次數")
                ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'))
                for i in range(len(counts)):
                    x_pos = (edges[i] + edges[i+1]) / 2
                    y_pos = counts[i]
                    if y_pos > 0:
                        ax2.text(x_pos, y_pos, str(int(counts[i])), ha='center', va='bottom', fontsize=9)
                st.pyplot(fig2)
                st.caption(f"經過 Monte Carlo 模擬後，最終資產的頻率分佈圖，並已去除前 {remove_low_pct}% 最低值與後 {remove_high_pct}% 最高值，以提供更具參考性的區間預測。")
    
                # 最終資產分佈表格
                hist_df = pd.DataFrame({
                    '資產下界': edges[:-1],
                    '資產上界': edges[1:],
                    '次數': counts.astype(int)
                })
                hist_df = hist_df[hist_df['次數'] > 0]
                hist_df['資產區間'] = hist_df.apply(lambda r: f"{int(r['資產下界']):,} ➔ {int(r['資產上界']):,}", axis=1)
                hist_df = hist_df[['資產區間', '次數']]
                st.dataframe(hist_df, use_container_width=True)
            else:
                 st.warning("模擬數據不足，無法繪製分佈圖。")
        else:
            st.warning("歷史日報酬率數據不足，無法執行 Monte Carlo 模擬。")
        
        st.markdown("</div>", unsafe_allow_html=True)
    elif do_mc:
        st.info("資料不足，無法執行 Monte Carlo 模擬 (至少需要 3 個交易日數據)。")

else:
    # 這是上傳檔案前的提示
    st.error("❌ 檔案讀取失敗或資料檔案為空。請確認：\n\n1. 您已將資料檔案命名為 **加權指數資料.xlsx**。\n2. 檔案與 `appV6.py` 位於**同一個資料夾**。\n3. 如果是網站部署，請檢查 GitHub 倉庫中是否有這個 Excel 檔案。")
