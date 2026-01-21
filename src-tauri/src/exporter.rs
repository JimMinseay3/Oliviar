use rust_xlsxwriter::*;
use serde_json::Value;
use std::path::PathBuf;

pub fn export_to_excel(
    file_path: PathBuf,
    columns: Vec<String>,
    data: Vec<Value>,
) -> Result<(), String> {
    let mut workbook = Workbook::new();
    let worksheet = workbook.add_worksheet();

    // Write headers
    for (col_idx, col_name) in columns.iter().enumerate() {
        worksheet
            .write_string(0, col_idx as u16, col_name)
            .map_err(|e| e.to_string())?;
    }

    // Write data
    for (row_idx, row_data) in data.iter().enumerate() {
        let row_idx = (row_idx + 1) as u32;
        if let Some(obj) = row_data.as_object() {
            for (col_idx, col_name) in columns.iter().enumerate() {
                if let Some(val) = obj.get(col_name) {
                    let col_idx = col_idx as u16;
                    match val {
                        Value::Number(n) => {
                            if let Some(f) = n.as_f64() {
                                worksheet.write_number(row_idx, col_idx, f).map_err(|e| e.to_string())?;
                            }
                        }
                        Value::String(s) => {
                            worksheet.write_string(row_idx, col_idx, s).map_err(|e| e.to_string())?;
                        }
                        _ => {
                            worksheet.write_string(row_idx, col_idx, &val.to_string()).map_err(|e| e.to_string())?;
                        }
                    }
                }
            }
        }
    }

    workbook.save(file_path).map_err(|e| e.to_string())?;
    Ok(())
}
