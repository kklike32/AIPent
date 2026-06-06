use std::{
    collections::HashMap,
    fs,
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::Mutex,
    thread,
};

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tauri::{
    menu::MenuBuilder,
    tray::TrayIconBuilder,
    AppHandle, Emitter, Manager, State,
};

const RECORDER_EVENT: &str = "recorder-event";

#[derive(Default)]
struct RecorderProcessState {
    pid: Mutex<Option<u32>>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AppSettings {
    screenshot_interval_seconds: u32,
    chunk_interval_seconds: u32,
    raw_data_ttl_seconds: u32,
    llm_provider: String,
    llm_model: String,
    google_cloud_project: String,
    google_cloud_location: String,
    insforge_base_url: String,
    insforge_project_id: String,
    insforge_api_key: String,
    insforge_auth_enabled: bool,
    insforge_auth_token: String,
    insforge_current_user_id: String,
    default_workflow_visibility: String,
    enable_team_sharing: bool,
    cloud_sync_enabled: bool,
    has_insforge_api_key: bool,
    has_insforge_auth_token: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(default)]
struct StoredSettings {
    screenshot_interval_seconds: u32,
    chunk_interval_seconds: u32,
    raw_data_ttl_seconds: u32,
    llm_provider: String,
    llm_model: String,
    google_cloud_project: String,
    google_cloud_location: String,
    insforge_base_url: String,
    insforge_project_id: String,
    insforge_api_key: String,
    insforge_auth_enabled: bool,
    insforge_auth_token: String,
    insforge_current_user_id: String,
    default_workflow_visibility: String,
    enable_team_sharing: bool,
    cloud_sync_enabled: bool,
}

impl Default for StoredSettings {
    fn default() -> Self {
        Self {
            screenshot_interval_seconds: 2,
            chunk_interval_seconds: 6,
            raw_data_ttl_seconds: 300,
            llm_provider: "vertex_gemini".to_string(),
            llm_model: "gemini-1.5-pro".to_string(),
            google_cloud_project: String::new(),
            google_cloud_location: "us-central1".to_string(),
            insforge_base_url: String::new(),
            insforge_project_id: String::new(),
            insforge_api_key: String::new(),
            insforge_auth_enabled: true,
            insforge_auth_token: String::new(),
            insforge_current_user_id: String::new(),
            default_workflow_visibility: "private".to_string(),
            enable_team_sharing: true,
            cloud_sync_enabled: false,
        }
    }
}

impl StoredSettings {
    fn to_public(&self) -> AppSettings {
        AppSettings {
            screenshot_interval_seconds: self.screenshot_interval_seconds,
            chunk_interval_seconds: self.chunk_interval_seconds,
            raw_data_ttl_seconds: self.raw_data_ttl_seconds,
            llm_provider: self.llm_provider.clone(),
            llm_model: self.llm_model.clone(),
            google_cloud_project: self.google_cloud_project.clone(),
            google_cloud_location: self.google_cloud_location.clone(),
            insforge_base_url: self.insforge_base_url.clone(),
            insforge_project_id: self.insforge_project_id.clone(),
            insforge_api_key: mask_secret(&self.insforge_api_key),
            insforge_auth_enabled: self.insforge_auth_enabled,
            insforge_auth_token: mask_secret(&self.insforge_auth_token),
            insforge_current_user_id: self.insforge_current_user_id.clone(),
            default_workflow_visibility: self.default_workflow_visibility.clone(),
            enable_team_sharing: self.enable_team_sharing,
            cloud_sync_enabled: self.cloud_sync_enabled,
            has_insforge_api_key: !self.insforge_api_key.is_empty(),
            has_insforge_auth_token: !self.insforge_auth_token.is_empty(),
        }
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .expect("desktop/src-tauri should be nested under repo root")
        .to_path_buf()
}

fn settings_path() -> PathBuf {
    repo_root().join("desktop").join(".workflow-tracker.json")
}

fn env_path() -> PathBuf {
    repo_root().join(".env")
}

fn mask_secret(secret: &str) -> String {
    if secret.is_empty() {
        return String::new();
    }
    let suffix_len = secret.len().min(4);
    format!("{}{}", "*".repeat(8), &secret[secret.len() - suffix_len..])
}

fn parse_env_file(path: &Path) -> HashMap<String, String> {
    let mut values = HashMap::new();
    let Ok(content) = fs::read_to_string(path) else {
        return values;
    };

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        if let Some((key, value)) = trimmed.split_once('=') {
            values.insert(key.to_string(), value.to_string());
        }
    }
    values
}

fn load_stored_settings() -> Result<StoredSettings, String> {
    let path = settings_path();
    if path.exists() {
        let content = fs::read_to_string(&path).map_err(|error| error.to_string())?;
        let mut settings =
            serde_json::from_str::<StoredSettings>(&content).map_err(|error| error.to_string())?;
        let env = parse_env_file(&env_path());

        if settings.insforge_auth_token.is_empty() {
            settings.insforge_auth_token = env.get("INSFORGE_AUTH_TOKEN").cloned().unwrap_or_default();
        }
        if settings.insforge_current_user_id.is_empty() {
            settings.insforge_current_user_id = env
                .get("INSFORGE_CURRENT_USER_ID")
                .cloned()
                .unwrap_or_default();
        }
        if settings.default_workflow_visibility.is_empty() {
            settings.default_workflow_visibility = env
                .get("DEFAULT_WORKFLOW_VISIBILITY")
                .cloned()
                .unwrap_or_else(|| "private".to_string());
        }
        if let Some(value) = env.get("INSFORGE_AUTH_ENABLED") {
            settings.insforge_auth_enabled =
                matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "on");
        }
        if let Some(value) = env.get("ENABLE_TEAM_SHARING") {
            settings.enable_team_sharing =
                matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "on");
        }
        return Ok(settings);
    }

    let env = parse_env_file(&env_path());
    let defaults = StoredSettings::default();
    Ok(StoredSettings {
        screenshot_interval_seconds: env
            .get("SCREENSHOT_INTERVAL_SECONDS")
            .and_then(|value| value.parse().ok())
            .unwrap_or(defaults.screenshot_interval_seconds),
        chunk_interval_seconds: env
            .get("CHUNK_INTERVAL_SECONDS")
            .and_then(|value| value.parse().ok())
            .unwrap_or(defaults.chunk_interval_seconds),
        raw_data_ttl_seconds: env
            .get("RAW_DATA_TTL_SECONDS")
            .and_then(|value| value.parse().ok())
            .unwrap_or(defaults.raw_data_ttl_seconds),
        llm_provider: env
            .get("LLM_PROVIDER")
            .cloned()
            .unwrap_or(defaults.llm_provider),
        llm_model: env.get("LLM_MODEL").cloned().unwrap_or(defaults.llm_model),
        google_cloud_project: env.get("GOOGLE_CLOUD_PROJECT").cloned().unwrap_or_default(),
        google_cloud_location: env
            .get("GOOGLE_CLOUD_LOCATION")
            .cloned()
            .unwrap_or(defaults.google_cloud_location),
        insforge_base_url: env.get("INSFORGE_BASE_URL").cloned().unwrap_or_default(),
        insforge_project_id: env.get("INSFORGE_PROJECT_ID").cloned().unwrap_or_default(),
        insforge_api_key: env.get("INSFORGE_API_KEY").cloned().unwrap_or_default(),
        insforge_auth_enabled: env
            .get("INSFORGE_AUTH_ENABLED")
            .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "on"))
            .unwrap_or(defaults.insforge_auth_enabled),
        insforge_auth_token: env.get("INSFORGE_AUTH_TOKEN").cloned().unwrap_or_default(),
        insforge_current_user_id: env
            .get("INSFORGE_CURRENT_USER_ID")
            .cloned()
            .unwrap_or_default(),
        default_workflow_visibility: env
            .get("DEFAULT_WORKFLOW_VISIBILITY")
            .cloned()
            .unwrap_or(defaults.default_workflow_visibility),
        enable_team_sharing: env
            .get("ENABLE_TEAM_SHARING")
            .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "on"))
            .unwrap_or(defaults.enable_team_sharing),
        cloud_sync_enabled: env
            .get("ENABLE_CLOUD_SYNC")
            .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "on"))
            .unwrap_or(defaults.cloud_sync_enabled),
    })
}

fn persist_env(settings: &StoredSettings) -> Result<(), String> {
    let path = env_path();
    let existing = fs::read_to_string(&path).unwrap_or_default();
    let mut lines: Vec<String> = if existing.is_empty() {
        Vec::new()
    } else {
        existing.lines().map(ToOwned::to_owned).collect()
    };

    let mut updates = HashMap::from([
        (
            "SCREENSHOT_INTERVAL_SECONDS".to_string(),
            settings.screenshot_interval_seconds.to_string(),
        ),
        (
            "CHUNK_INTERVAL_SECONDS".to_string(),
            settings.chunk_interval_seconds.to_string(),
        ),
        (
            "RAW_DATA_TTL_SECONDS".to_string(),
            settings.raw_data_ttl_seconds.to_string(),
        ),
        (
            "ENABLE_CLOUD_SYNC".to_string(),
            settings.cloud_sync_enabled.to_string(),
        ),
        ("UPLOAD_RAW_EVENTS".to_string(), "false".to_string()),
        ("UPLOAD_SCREENSHOTS".to_string(), "false".to_string()),
        ("UPLOAD_OCR_TEXT".to_string(), "false".to_string()),
        ("UPLOAD_ONLY_SUMMARIES".to_string(), "true".to_string()),
        ("LLM_PROVIDER".to_string(), settings.llm_provider.clone()),
        ("LLM_MODEL".to_string(), settings.llm_model.clone()),
        (
            "GOOGLE_CLOUD_PROJECT".to_string(),
            settings.google_cloud_project.clone(),
        ),
        (
            "GOOGLE_CLOUD_LOCATION".to_string(),
            settings.google_cloud_location.clone(),
        ),
        (
            "INSFORGE_BASE_URL".to_string(),
            settings.insforge_base_url.clone(),
        ),
        (
            "INSFORGE_PROJECT_ID".to_string(),
            settings.insforge_project_id.clone(),
        ),
        (
            "INSFORGE_AUTH_ENABLED".to_string(),
            settings.insforge_auth_enabled.to_string(),
        ),
        (
            "INSFORGE_CURRENT_USER_ID".to_string(),
            settings.insforge_current_user_id.clone(),
        ),
        (
            "DEFAULT_WORKFLOW_VISIBILITY".to_string(),
            settings.default_workflow_visibility.clone(),
        ),
        (
            "ENABLE_TEAM_SHARING".to_string(),
            settings.enable_team_sharing.to_string(),
        ),
    ]);

    if !settings.insforge_api_key.is_empty() {
        updates.insert("INSFORGE_API_KEY".to_string(), settings.insforge_api_key.clone());
    }
    if !settings.insforge_auth_token.is_empty() {
        updates.insert(
            "INSFORGE_AUTH_TOKEN".to_string(),
            settings.insforge_auth_token.clone(),
        );
    }

    for line in &mut lines {
        if let Some((key, _value)) = line.split_once('=') {
            if let Some(next) = updates.remove(key.trim()) {
                *line = format!("{key}={next}");
            }
        }
    }

    for (key, value) in updates {
        lines.push(format!("{key}={value}"));
    }

    fs::write(path, format!("{}\n", lines.join("\n"))).map_err(|error| error.to_string())
}

fn persist_settings(settings: &StoredSettings) -> Result<(), String> {
    let content = serde_json::to_string_pretty(settings).map_err(|error| error.to_string())?;
    fs::write(settings_path(), content).map_err(|error| error.to_string())?;
    persist_env(settings)
}

fn merge_settings(input: AppSettings) -> Result<StoredSettings, String> {
    let existing = load_stored_settings()?;
    let insforge_api_key = if input.insforge_api_key.is_empty()
        || input.insforge_api_key == mask_secret(&existing.insforge_api_key)
    {
        existing.insforge_api_key
    } else {
        input.insforge_api_key
    };
    let insforge_auth_token = if input.insforge_auth_token.is_empty()
        || input.insforge_auth_token == mask_secret(&existing.insforge_auth_token)
    {
        existing.insforge_auth_token
    } else {
        input.insforge_auth_token
    };

    Ok(StoredSettings {
        screenshot_interval_seconds: input.screenshot_interval_seconds.max(1),
        chunk_interval_seconds: input.chunk_interval_seconds.max(1),
        raw_data_ttl_seconds: input.raw_data_ttl_seconds.max(60),
        llm_provider: input.llm_provider,
        llm_model: input.llm_model,
        google_cloud_project: input.google_cloud_project,
        google_cloud_location: input.google_cloud_location,
        insforge_base_url: input.insforge_base_url,
        insforge_project_id: input.insforge_project_id,
        insforge_api_key,
        insforge_auth_enabled: input.insforge_auth_enabled,
        insforge_auth_token,
        insforge_current_user_id: input.insforge_current_user_id,
        default_workflow_visibility: input.default_workflow_visibility,
        enable_team_sharing: input.enable_team_sharing,
        cloud_sync_enabled: input.cloud_sync_enabled,
    })
}

fn detect_python(repo_root: &Path) -> String {
    let venv_python = repo_root.join(".venv").join("bin").join("python");
    if venv_python.exists() {
        return venv_python.to_string_lossy().into_owned();
    }
    "python3".to_string()
}

fn emit_error(app: &AppHandle, message: impl Into<String>, recoverable: bool) {
    let _ = app.emit(
        RECORDER_EVENT,
        json!({
            "type": "error",
            "message": message.into(),
            "recoverable": recoverable,
        }),
    );
}

fn spawn_output_thread(app: AppHandle, reader: impl BufRead + Send + 'static) {
    thread::spawn(move || {
        for line in reader.lines() {
            match line {
                Ok(content) if !content.trim().is_empty() => match serde_json::from_str::<Value>(&content) {
                    Ok(payload) => {
                        let _ = app.emit(RECORDER_EVENT, payload);
                    }
                    Err(_) => emit_error(&app, content, true),
                },
                Ok(_) => {}
                Err(error) => emit_error(&app, error.to_string(), true),
            }
        }
    });
}

fn with_pid<R>(
    state: &State<'_, RecorderProcessState>,
    f: impl FnOnce(Option<u32>) -> Result<R, String>,
) -> Result<R, String> {
    let pid = *state.pid.lock().map_err(|_| "recorder state lock poisoned".to_string())?;
    f(pid)
}

fn send_signal(pid: u32, signal: i32) -> Result<(), String> {
    let result = unsafe { libc::kill(pid as i32, signal) };
    if result == 0 {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error().to_string())
    }
}

fn show_dashboard_window(app: &AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("main")
        .ok_or_else(|| "main window not found".to_string())?;
    window.show().map_err(|error| error.to_string())?;
    window.set_focus().map_err(|error| error.to_string())
}

fn start_recorder_internal(app: AppHandle, state: &State<'_, RecorderProcessState>) -> Result<(), String> {
    with_pid(state, |pid| {
        if pid.is_some() {
            return Err("recorder is already running".to_string());
        }
        Ok(())
    })?;

    let settings = load_stored_settings()?;
    let root = repo_root();
    let python = detect_python(&root);
    let mut command = Command::new(python);
    command
        .arg("-m")
        .arg("tracker.cli")
        .arg("start")
        .arg("--jsonl")
        .arg("--screenshot-interval")
        .arg(settings.screenshot_interval_seconds.to_string())
        .arg("--chunk-interval")
        .arg(settings.chunk_interval_seconds.to_string())
        .arg("--visibility")
        .arg(settings.default_workflow_visibility.clone())
        .arg("--llm-provider")
        .arg(settings.llm_provider.clone())
        .current_dir(&root)
        .env("PYTHONPATH", root.join("src"))
        .env("RAW_DATA_TTL_SECONDS", settings.raw_data_ttl_seconds.to_string())
        .env("LLM_MODEL", settings.llm_model.clone())
        .env("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project.clone())
        .env("GOOGLE_CLOUD_LOCATION", settings.google_cloud_location.clone())
        .env("INSFORGE_BASE_URL", settings.insforge_base_url.clone())
        .env("INSFORGE_PROJECT_ID", settings.insforge_project_id.clone())
        .env("INSFORGE_API_KEY", settings.insforge_api_key.clone())
        .env(
            "INSFORGE_AUTH_ENABLED",
            if settings.insforge_auth_enabled { "true" } else { "false" },
        )
        .env("INSFORGE_AUTH_TOKEN", settings.insforge_auth_token.clone())
        .env(
            "INSFORGE_CURRENT_USER_ID",
            settings.insforge_current_user_id.clone(),
        )
        .env(
            "DEFAULT_WORKFLOW_VISIBILITY",
            settings.default_workflow_visibility.clone(),
        )
        .env(
            "ENABLE_TEAM_SHARING",
            if settings.enable_team_sharing { "true" } else { "false" },
        )
        .env(
            "ENABLE_CLOUD_SYNC",
            if settings.cloud_sync_enabled { "true" } else { "false" },
        )
        .env("UPLOAD_RAW_EVENTS", "false")
        .env("UPLOAD_SCREENSHOTS", "false")
        .env("UPLOAD_OCR_TEXT", "false")
        .env("UPLOAD_ONLY_SUMMARIES", "true")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    if settings.cloud_sync_enabled {
        command.arg("--cloud-sync");
    } else {
        command.arg("--no-cloud-sync");
    }

    let mut child = command.spawn().map_err(|error| error.to_string())?;
    let pid = child.id();
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "failed to capture recorder stdout".to_string())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "failed to capture recorder stderr".to_string())?;

    {
        let mut guard = state.pid.lock().map_err(|_| "recorder state lock poisoned".to_string())?;
        *guard = Some(pid);
    }

    spawn_output_thread(app.clone(), BufReader::new(stdout));
    spawn_output_thread(app.clone(), BufReader::new(stderr));

    let app_handle = app.clone();
    thread::spawn(move || {
        let _ = child.wait();
        if let Ok(mut global_pid) = app_handle.state::<RecorderProcessState>().pid.lock() {
            *global_pid = None;
        }
    });

    Ok(())
}

#[tauri::command]
fn load_settings() -> Result<AppSettings, String> {
    load_stored_settings().map(|settings| settings.to_public())
}

#[tauri::command]
fn save_settings(settings: AppSettings) -> Result<AppSettings, String> {
    let merged = merge_settings(settings)?;
    persist_settings(&merged)?;
    Ok(merged.to_public())
}

#[tauri::command]
fn start_recorder(app: AppHandle, state: State<'_, RecorderProcessState>) -> Result<(), String> {
    start_recorder_internal(app, &state)
}

#[tauri::command]
fn stop_recorder(state: State<'_, RecorderProcessState>) -> Result<(), String> {
    with_pid(&state, |pid| match pid {
        Some(pid) => send_signal(pid, libc::SIGINT),
        None => Err("recorder is not running".to_string()),
    })
}

#[tauri::command]
fn pause_recorder(state: State<'_, RecorderProcessState>) -> Result<(), String> {
    with_pid(&state, |pid| match pid {
        Some(pid) => send_signal(pid, libc::SIGUSR1),
        None => Err("recorder is not running".to_string()),
    })
}

#[tauri::command]
fn resume_recorder(state: State<'_, RecorderProcessState>) -> Result<(), String> {
    with_pid(&state, |pid| match pid {
        Some(pid) => send_signal(pid, libc::SIGUSR2),
        None => Err("recorder is not running".to_string()),
    })
}

#[tauri::command]
fn show_dashboard(app: AppHandle) -> Result<(), String> {
    show_dashboard_window(&app)
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .manage(RecorderProcessState::default())
        .menu(|app| {
            MenuBuilder::new(app)
                .text("start_recording", "Start Recording")
                .text("stop_recording", "Stop Recording")
                .text("show_dashboard", "Show Dashboard")
                .separator()
                .text("quit", "Quit")
                .build()
        })
        .on_menu_event(|app, event| {
            let id = event.id().0.as_str();
            match id {
                "start_recording" => {
                    let state = app.state::<RecorderProcessState>();
                    if let Err(error) = start_recorder_internal(app.clone(), &state) {
                        emit_error(app, error, true);
                    }
                }
                "stop_recording" => {
                    let state = app.state::<RecorderProcessState>();
                    if let Err(error) = stop_recorder(state) {
                        emit_error(app, error, true);
                    }
                }
                "show_dashboard" => {
                    if let Err(error) = show_dashboard_window(app) {
                        emit_error(app, error, true);
                    }
                }
                "quit" => app.exit(0),
                _ => {}
            }
        })
        .setup(|app| {
            let tray_menu = MenuBuilder::new(app)
                .text("start_recording", "Start Recording")
                .text("stop_recording", "Stop Recording")
                .text("show_dashboard", "Show Dashboard")
                .separator()
                .text("quit", "Quit")
                .build()?;

            TrayIconBuilder::with_id("workflow-tray")
                .menu(&tray_menu)
                .show_menu_on_left_click(true)
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            load_settings,
            save_settings,
            start_recorder,
            stop_recorder,
            pause_recorder,
            resume_recorder,
            show_dashboard
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
