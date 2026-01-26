mod fetcher;
mod exporter;

use std::process::Command;
use serde_json::Value;
use std::path::PathBuf;

#[tauri::command]
async fn export_excel(
    path: String,
    filename: String,
    columns: Vec<String>,
    data: Vec<Value>,
) -> Result<String, String> {
    let mut file_path = PathBuf::from(path);
    if !file_path.exists() {
        std::fs::create_dir_all(&file_path).map_err(|e| e.to_string())?;
    }
    file_path.push(filename);
    
    exporter::export_to_excel(file_path.clone(), columns, data)?;
    Ok(file_path.to_string_lossy().to_string())
}

#[tauri::command]
async fn analyze_stock(symbol: String, download: bool, output_dir: Option<String>) -> Result<Value, String> {
    // 1. 获取当前工作目录
    let current_dir = std::env::current_dir().map_err(|e| e.to_string())?;
    
    // 寻找 python 解释器和 bridge.py
    let (python_path, bridge_path) = {
        let mut venv_path = current_dir.join(".venv");
        let mut py_exe = if cfg!(windows) {
            venv_path.join("Scripts").join("python.exe")
        } else {
            venv_path.join("bin").join("python")
        };
        let mut b_path = current_dir.join("core").join("bridge.py");
        
        if !py_exe.exists() {
            // 尝试在父目录寻找 (如果在 src-tauri 目录下运行)
            let parent_dir = current_dir.parent().unwrap_or(&current_dir);
            venv_path = parent_dir.join(".venv");
            py_exe = if cfg!(windows) {
                venv_path.join("Scripts").join("python.exe")
            } else {
                venv_path.join("bin").join("python")
            };
            b_path = parent_dir.join("core").join("bridge.py");
        }
        (py_exe, b_path)
    };

    if !python_path.exists() {
        return Err(format!("Python virtual environment not found. Checked current and parent directory."));
    }

    if !bridge_path.exists() {
        return Err(format!("bridge.py not found at {:?}", bridge_path));
    }

    // 运行 bridge.py 脚本
    let mut cmd = Command::new(python_path);
    cmd.arg(bridge_path).arg(&symbol);
    
    if download {
        cmd.arg("--download");
    }

    if let Some(dir) = output_dir {
        cmd.arg("--output-dir").arg(dir);
    }

    let output = cmd.output().map_err(|e| e.to_string())?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Python script failed: {}", stderr));
    }

    let stdout = String::from_utf8_lossy(&output.stdout);
    
    // 解析 JSON 输出
    let json: Value = serde_json::from_str(&stdout).map_err(|e| format!("Failed to parse JSON: {}", e))?;
    Ok(json)
}

#[tauri::command]
async fn list_reports(output_dir: Option<String>) -> Result<Value, String> {
    let current_dir = std::env::current_dir().map_err(|e| e.to_string())?;
    let data_dir = if let Some(dir) = output_dir {
        std::path::PathBuf::from(dir)
    } else {
        let mut d = current_dir.join("data");
        if !d.exists() {
            // 尝试在父目录寻找
            let parent_data = current_dir.parent().unwrap_or(&current_dir).join("data");
            if parent_data.exists() {
                d = parent_data;
            }
        }
        d
    };
    
    if !data_dir.exists() {
        return Ok(serde_json::json!([]));
    }

    let mut reports = Vec::new();
    for entry in std::fs::read_dir(data_dir).map_err(|e| e.to_string())? {
        let entry = entry.map_err(|e| e.to_string())?;
        let path = entry.path();
        if path.is_dir() {
            let dir_name = path.file_name().unwrap().to_string_lossy().to_string();
            let parts: Vec<&str> = dir_name.split('_').collect();
            if parts.len() >= 2 {
                let symbol = parts[0];
                let name = parts[1];
                
                for file_entry in std::fs::read_dir(&path).map_err(|e| e.to_string())? {
                    let file_entry = file_entry.map_err(|e| e.to_string())?;
                    let file_path = file_entry.path();
                    if file_path.extension().map_or(false, |ext| ext == "pdf") {
                        let file_name = file_path.file_name().unwrap().to_string_lossy();
                        // 格式通常为: 2025-04-28_2025年一季度报告.pdf
                        let file_parts: Vec<&str> = file_name.split('_').collect();
                        if file_parts.len() >= 2 {
                            reports.push(serde_json::json!({
                                "symbol": symbol,
                                "name": name,
                                "date": file_parts[0],
                                "title": file_parts[1].replace(".pdf", ""),
                                "path": file_path.to_string_lossy()
                            }));
                        }
                    }
                }
            }
        }
    }
    
    Ok(serde_json::json!(reports))
}

#[tauri::command]
async fn open_file(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        Command::new("cmd")
            .args(["/C", "start", "", &path])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        Command::new("xdg-open")
            .arg(&path)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command]
async fn show_in_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        Command::new("explorer")
            .args(["/select,", &path])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "macos")]
    {
        Command::new("open")
            .args(["-R", &path])
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    #[cfg(target_os = "linux")]
    {
        let path = std::path::Path::new(&path);
        let parent = path.parent().unwrap_or(path);
        Command::new("xdg-open")
            .arg(parent)
            .spawn()
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .plugin(tauri_plugin_dialog::init())
    .invoke_handler(tauri::generate_handler![analyze_stock, list_reports, open_file, show_in_folder, export_excel])
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
