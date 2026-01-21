#![allow(dead_code)]
use serde_json::{json, Value};
use std::collections::HashMap;
use chrono::Local;

pub async fn fetch_all_data(symbol: &str) -> Result<Value, String> {
    let market = if symbol.starts_with('6') || symbol.starts_with('9') {
        "1"
    } else {
        "0"
    };
    let secid = format!("{}.{}", market, symbol);

    let client = reqwest::Client::builder()
        .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        .build()
        .map_err(|e| e.to_string())?;

    // Define all tasks
    let t1 = fetch_realtime(&client, &secid);
    let t2 = fetch_history(&client, &secid);
    let t3 = fetch_fund_flow(&client, &secid);
    let t4 = fetch_financial_indicators(&client, symbol);

    // Run all tasks concurrently
    let (r1, r2, r3, r4) = tokio::join!(t1, t2, t3, t4);

    let realtime = r1.unwrap_or(json!({}));
    let history = r2.unwrap_or(json!([]));
    let fund_flow = r3.unwrap_or(json!([]));
    let financials = r4.unwrap_or(json!({}));

    // Process and merge data into the format expected by the frontend
    let mut report_data = HashMap::new();
    
    // Basic info from realtime
    let rt_data = &realtime["data"];
    let name = rt_data["f58"].as_str().unwrap_or(symbol);
    let industry = rt_data["f127"].as_str().unwrap_or("N/A");
    
    report_data.insert("分析标的".to_string(), json!(name));
    report_data.insert("证券代码".to_string(), json!(symbol));
    report_data.insert("所属行业".to_string(), json!(industry));
    report_data.insert("分析时间".to_string(), json!(Local::now().format("%Y-%m-%d %H:%M:%S").to_string()));
    
    // Top-level indicators (Overview) - Properly formatted
    let current_price = rt_data["f43"].as_f64().unwrap_or(0.0);
    report_data.insert("现价".to_string(), json!(current_price));
    report_data.insert("涨跌".to_string(), rt_data["f44"].clone());
    let pct = rt_data["f3"].as_f64().unwrap_or(0.0); 
    report_data.insert("涨幅".to_string(), json!(format!("{:.2}%", pct)));
    report_data.insert("成交额".to_string(), json!(format!("{:.2}亿", rt_data["f6"].as_f64().unwrap_or(0.0) / 1e8)));
    report_data.insert("换手率%".to_string(), json!(format!("{}%", rt_data["f8"])));
    report_data.insert("振幅".to_string(), json!(format!("{}%", rt_data["f7"])));
    report_data.insert("最高".to_string(), rt_data["f44"].clone());
    report_data.insert("最低".to_string(), rt_data["f45"].clone());
    report_data.insert("开盘".to_string(), rt_data["f46"].clone());
    report_data.insert("昨收".to_string(), rt_data["f60"].clone());
    report_data.insert("量比".to_string(), rt_data["f10"].clone());
    
    // Formatting PE/PB from API (values are usually multiplied by 100)
    let pe_ttm = rt_data["f162"].as_f64().unwrap_or(0.0) / 100.0;
    let pe_static = rt_data["f163"].as_f64().unwrap_or(0.0) / 100.0;
    let pe_dynamic = rt_data["f164"].as_f64().unwrap_or(0.0) / 100.0;
    let pb_mrq = rt_data["f167"].as_f64().unwrap_or(0.0) / 100.0;
    
    report_data.insert("市盈率(TTM)".to_string(), json!(format!("{:.2}", pe_ttm)));
    report_data.insert("市盈(静)".to_string(), json!(format!("{:.2}", pe_static)));
    report_data.insert("市盈(动)".to_string(), json!(format!("{:.2}", pe_dynamic)));
    report_data.insert("市净率(MRQ)".to_string(), json!(format!("{:.2}", pb_mrq)));
    
    let total_mv = rt_data["f116"].as_f64().unwrap_or(0.0);
    let circ_mv = rt_data["f117"].as_f64().unwrap_or(0.0);
    report_data.insert("总市值".to_string(), json!(format!("{:.2}亿", total_mv / 1e8)));
    report_data.insert("流通市值".to_string(), json!(format!("{:.2}亿", circ_mv / 1e8)));
    
    // Calculate total shares and circulating shares (needed for historical calculation)
    let total_shares = if current_price > 0.0 { total_mv / current_price } else { 0.0 };
    let circ_shares = if current_price > 0.0 { circ_mv / current_price } else { 0.0 };
    
    report_data.insert("总股本".to_string(), json!(format!("{:.2}亿股", total_shares / 1e8)));
    report_data.insert("流通股本".to_string(), json!(format!("{:.2}亿股", circ_shares / 1e8)));
    report_data.insert("股息率".to_string(), json!(format!("{}%", rt_data["f108"])));
    
    // Depth data (sum of volumes for top 5 levels)
    let bid_vol = rt_data["f12"].as_f64().unwrap_or(0.0) + rt_data["f14"].as_f64().unwrap_or(0.0) + rt_data["f16"].as_f64().unwrap_or(0.0) + rt_data["f18"].as_f64().unwrap_or(0.0) + rt_data["f20"].as_f64().unwrap_or(0.0);
    let ask_vol = rt_data["f32"].as_f64().unwrap_or(0.0) + rt_data["f34"].as_f64().unwrap_or(0.0) + rt_data["f36"].as_f64().unwrap_or(0.0) + rt_data["f38"].as_f64().unwrap_or(0.0) + rt_data["f40"].as_f64().unwrap_or(0.0);
    let depth_str = format!("买五量:{:.0}, 卖五量:{:.0}", bid_vol, ask_vol);
    let liquidity_str = if bid_vol + ask_vol > 50000.0 { "极佳" } else if bid_vol + ask_vol > 10000.0 { "良好" } else { "一般" };
    report_data.insert("买卖盘深度".to_string(), json!(depth_str));
    report_data.insert("流动性评估".to_string(), json!(liquidity_str));
    report_data.insert("行业相关性".to_string(), json!("N/A")); // Default

    // Financial Indicators Mapping for each row
    let fin_reports = financials.get("data").and_then(|d| d.as_array()).cloned().unwrap_or_default();
    
    let mapping = [
        ("TOTAL_OPERATE_REVENUE", "营业总收入"),
        ("OPERATE_PROFIT", "营业利润"),
        ("PARENT_NETPROFIT", "归母净利润"),
        ("DEDUCT_PARENT_NETPROFIT", "扣非净利润"),
        ("ROE_WEIGHT", "净资产收益率(ROE)"),
        ("GROSS_PROFIT_MARGIN", "销售毛利率"),
        ("NET_PROFIT_MARGIN", "销售净利率"),
        ("ASSET_LIAB_RATIO", "资产负债率"),
        ("GOODWILL", "商誉"),
        ("BASIC_EPS", "基本每股收益"),
        ("BPS", "每股净资产"),
        ("PER_NET_CASH", "每股经营现金流"),
        ("PER_UNDISTRIBUTE_PROFIT", "每股未分配利润"),
        ("PER_CAPITAL_RESERVE", "每股公积金"),
        ("TOTAL_OPERATE_REVENUE_YOY", "营业总收入同比"),
        ("OPERATE_PROFIT_YOY", "营业利润同比"),
        ("PARENT_NETPROFIT_YOY", "归母净利润同比"),
        ("DEDUCT_PARENT_NETPROFIT_YOY", "扣非净利润同比"),
    ];

    // Merge latest financials into report_data summary
    if let Some(fin_data) = fin_reports.first() {
        for (src, target) in mapping {
            if let Some(val) = fin_data.get(src) {
                let val_str = format_financial_value(val, target);
                report_data.insert(target.to_string(), json!(val_str));
            }
        }
    }

    // Sort fin_reports by REPORT_DATE descending (already should be, but let's be safe)
    let mut sorted_fin = fin_reports.clone();
    sorted_fin.sort_by(|a, b| b["REPORT_DATE"].as_str().unwrap_or("").cmp(a["REPORT_DATE"].as_str().unwrap_or("")));

    // Pre-calculate all closing prices for HV calculation
    let hist_list = history.as_array().map(|v| v.clone()).unwrap_or_default();
    let closes: Vec<f64> = hist_list.iter()
        .filter_map(|v| v.as_str())
        .filter_map(|s| s.split(',').nth(2)) // f53 is close
        .filter_map(|s| s.parse::<f64>().ok())
        .collect();

    // Pre-calculate all daily log returns
    let mut log_returns = Vec::new();
    for i in 1..closes.len() {
        if closes[i-1] > 0.0 {
            log_returns.push((closes[i] / closes[i-1]).ln());
        } else {
            log_returns.push(0.0);
        }
    }

    // Historical data for Excel
    let mut excel_data = Vec::new();
    let ff_map: HashMap<String, &Value> = fund_flow.as_array()
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| (s.split(',').next().unwrap_or("").to_string(), v))).collect())
        .unwrap_or_default();

    for (idx, h) in hist_list.iter().enumerate() {
        // Skip first part, show last 30 days in Excel
        let total = hist_list.len();
        if idx < total.saturating_sub(30) { continue; }

        if let Some(s) = h.as_str() {
            let parts: Vec<&str> = s.split(',').collect();
            if parts.len() >= 11 {
                let date = parts[0];
                let open = parts[1];
                let close = parts[2];
                let high = parts[3];
                let low = parts[4];
                let vol = parts[5];
                let amount = parts[6];
                let amplitude = parts[7];
                let pct = parts[8];
                let change = parts[9];
                let turnover = parts[10];

                // Calculate HV20 and HV60 for THIS day
                // idx is the index in closes. log_returns[idx-1] is the return for day idx.
                // We need the window ending at log_returns[idx-1].
                let current_hv20 = if idx >= 20 {
                    let start = idx - 20;
                    let end = idx;
                    let window = &log_returns[start..end];
                    let hv = calculate_hv_from_returns(window);
                    format!("{:.2}%", hv * 100.0)
                } else {
                    "N/A".to_string()
                };

                let current_hv60 = if idx >= 60 {
                    let start = idx - 60;
                    let end = idx;
                    let window = &log_returns[start..end];
                    let hv = calculate_hv_from_returns(window);
                    format!("{:.2}%", hv * 100.0)
                } else {
                    "N/A".to_string()
                };

                // Calculate 昨收
                let prev_close = if idx > 0 {
                    hist_list[idx-1].as_str().and_then(|ps| ps.split(',').nth(2)).unwrap_or("N/A")
                } else {
                    "N/A"
                };

                let mut record = json!({
                    "日期": date,
                    "开盘": open,
                    "收盘": close,
                    "最高": high,
                    "最低": low,
                    "成交量": vol,
                    "成交额": format!("{:.2}亿", amount.parse::<f64>().unwrap_or(0.0) / 1e8),
                    "振幅": format!("{}%", amplitude),
                    "涨幅": format!("{}%", pct),
                    "涨跌": change,
                    "换手率%": format!("{}%", turnover),
                    "现价": close,
                    "昨收": prev_close,
                    "HV20": current_hv20,
                    "HV60": current_hv60,
                    "买卖盘深度": depth_str,
                    "流动性评估": liquidity_str,
                    "行业相关性": "N/A",
                });

                // Find the most recent financial report for THIS day
                let row_close = close.parse::<f64>().unwrap_or(0.0);
                if let Some(matching_report) = sorted_fin.iter().find(|r| {
                    let report_date = r["REPORT_DATE"].as_str().unwrap_or("");
                    date >= report_date // Row date is after or on report date
                }) {
                    // Calculate dynamic valuation for this day
                    let eps = matching_report["BASIC_EPS"].as_f64()
                        .or_else(|| matching_report["BASICEPS"].as_f64())
                        .unwrap_or(0.0);
                    let bps = matching_report["BPS"].as_f64().unwrap_or(0.0);
                    let revenue = matching_report["TOTAL_OPERATE_REVENUE"].as_f64().unwrap_or(0.0);
                    let cash_flow = matching_report["PER_NET_CASH"].as_f64().unwrap_or(0.0);
                    
                    if eps > 0.0 {
                        record["市盈率(TTM)"] = json!(format!("{:.2}", row_close / eps));
                    }
                    if bps > 0.0 {
                        record["市净率(MRQ)"] = json!(format!("{:.2}", row_close / bps));
                    }
                    if revenue > 0.0 && total_shares > 0.0 {
                        let ps = (row_close * total_shares) / revenue;
                        record["市销率(TTM)"] = json!(format!("{:.2}", ps));
                    }
                    if cash_flow > 0.0 {
                        record["市现率"] = json!(format!("{:.2}", row_close / cash_flow));
                    }
                    
                    record["总市值"] = json!(format!("{:.2}亿", (row_close * total_shares) / 1e8));
                    record["流通市值"] = json!(format!("{:.2}亿", (row_close * circ_shares) / 1e8));
                    record["总股本"] = json!(format!("{:.2}亿股", total_shares / 1e8));
                    record["流通股本"] = json!(format!("{:.2}亿股", circ_shares / 1e8));

                    // Add all other financial indicators from the matching report
                    for (src, target) in mapping {
                        if !record.as_object().unwrap().contains_key(target) {
                            // Try both with and without underscores
                            let val = matching_report.get(src)
                                .or_else(|| matching_report.get(&src.replace("_", "")));
                            
                            if let Some(v) = val {
                                record[target] = json!(format_financial_value(v, target));
                            }
                        }
                    }
                }

                // Add fund flow
                if let Some(ff) = ff_map.get(date) {
                    if let Some(ff_s) = ff.as_str() {
                        let ff_parts: Vec<&str> = ff_s.split(',').collect();
                        if ff_parts.len() >= 2 {
                             let main_flow = ff_parts[1].parse::<f64>().unwrap_or(0.0);
                             record["今日主力净流入(万元)"] = json!(format!("{:.2}", main_flow / 10000.0));
                        }
                    }
                } else {
                    record["今日主力净流入(万元)"] = json!("0.00");
                }

                // Final pass: Add remaining indicators from report_data summary
                for (key, val) in &report_data {
                    if !record.as_object().unwrap().contains_key(key) && key != "historical_data" {
                        record[key] = val.clone();
                    }
                }

                excel_data.push(record);
            }
        }
    }
    // Sort excel_data by date descending
    excel_data.sort_by(|a, b| b["日期"].as_str().unwrap_or("").cmp(a["日期"].as_str().unwrap_or("")));
    
    // Update report_data with the latest HV values for summary
    if let Some(latest) = excel_data.first() {
        report_data.insert("HV20".to_string(), latest["HV20"].clone());
        report_data.insert("HV60".to_string(), latest["HV60"].clone());
    }

    report_data.insert("historical_data".to_string(), json!(excel_data));

    Ok(json!(report_data))
}

async fn fetch_realtime(client: &reqwest::Client, secid: &str) -> Result<Value, String> {
    let url = format!("https://push2.eastmoney.com/api/qt/stock/get?secid={}&fields=f57,f58,f59,f60,f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f168,f169,f170,f116,f117,f162,f163,f164,f167,f108,f11,f12,f13,f14,f15,f16,f17,f18,f19,f20,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f62,f127,f128,f136,f115,f152", secid);
    let res = client.get(url).send().await.map_err(|e| e.to_string())?;
    res.json::<Value>().await.map_err(|e| e.to_string())
}

async fn fetch_history(client: &reqwest::Client, secid: &str) -> Result<Value, String> {
    let url = format!("https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=120", secid);
    let res = client.get(url).send().await.map_err(|e| e.to_string())?;
    let json: Value = res.json().await.map_err(|e| e.to_string())?;
    Ok(json["data"]["klines"].clone())
}

async fn fetch_fund_flow(client: &reqwest::Client, secid: &str) -> Result<Value, String> {
    let url = format!("https://push2.eastmoney.com/api/qt/stock/fflow/kline/get?secid={}&klt=101&lmt=120&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65", secid);
    let res = client.get(url).send().await.map_err(|e| e.to_string())?;
    let json: Value = res.json().await.map_err(|e| e.to_string())?;
    Ok(json["data"]["klines"].clone())
}

async fn fetch_financial_indicators(client: &reqwest::Client, symbol: &str) -> Result<Value, String> {
    let url = format!("https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_F10_FN_MAININDICATOR&columns=SECURITY_CODE,REPORT_DATE,TOTAL_OPERATE_REVENUE,OPERATE_PROFIT,PARENT_NETPROFIT,DEDUCT_PARENT_NETPROFIT,ROE_WEIGHT,GROSS_PROFIT_MARGIN,NET_PROFIT_MARGIN,ASSET_LIAB_RATIO,GOODWILL,BASIC_EPS,BPS,PER_NET_CASH,PER_UNDISTRIBUTE_PROFIT,PER_CAPITAL_RESERVE,TOTAL_OPERATE_REVENUE_YOY,OPERATE_PROFIT_YOY,PARENT_NETPROFIT_YOY,DEDUCT_PARENT_NETPROFIT_YOY&filter=(SECURITY_CODE=%22{}%22)&pageNumber=1&pageSize=8&sortColumns=REPORT_DATE&sortTypes=-1", symbol);
    let res = client.get(url).send().await.map_err(|e| e.to_string())?;
    res.json::<Value>().await.map_err(|e| e.to_string())
}

fn calculate_hv_from_returns(returns: &[f64]) -> f64 {
    let n = returns.len();
    if n < 2 {
        return 0.0;
    }
    let mean = returns.iter().sum::<f64>() / n as f64;
    let variance = returns.iter().map(|&r| (r - mean).powi(2)).sum::<f64>() / (n - 1) as f64;
    (variance * 252.0).sqrt()
}

fn format_financial_value(val: &Value, target: &str) -> String {
    if val.is_number() {
        let num = val.as_f64().unwrap_or(0.0);
        if target.contains("率") || target.contains("同比") || target.contains("ROE") {
            format!("{:.2}%", num)
        } else if num.abs() >= 1e8 {
            format!("{:.2}亿", num / 1e8)
        } else if num.abs() >= 1e4 {
            format!("{:.2}万", num / 1e4)
        } else {
            format!("{:.2}", num)
        }
    } else {
        let s = val.as_str().unwrap_or("N/A");
        if s.is_empty() || s == "null" {
            "N/A".to_string()
        } else {
            s.to_string()
        }
    }
}
