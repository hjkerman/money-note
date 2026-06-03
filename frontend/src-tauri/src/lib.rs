#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  // 웹 프론트엔드를 그대로 감싸는 얇은 데스크탑 앱 진입점이다.
  tauri::Builder::default()
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
