import AppKit
import Darwin
import Foundation

@MainActor
final class TrackerProcessController: ObservableObject {
    enum CaptureState: String {
        case idle
        case starting
        case running
        case stopping
        case error
    }

    @Published private(set) var state: CaptureState = .idle
    @Published private(set) var detailText = "Ready to capture."
    @Published private(set) var lastSessionID: String?
    @Published private(set) var lastLogLine = "Waiting to start."
    @Published private(set) var previewText = "No generated steps yet."
    @Published private(set) var isSyncing = false
    @Published private(set) var isCurrentSessionSynced = false

    let configuration: TrackerLaunchConfiguration
    private var process: Process?
    private var outputPipe: Pipe?
    private var errorPipe: Pipe?
    private var buffer = ""
    private let fileManager = FileManager.default
    private let stopSaveGracePeriod: TimeInterval = 300

    init(configuration: TrackerLaunchConfiguration = .makeDefault()) {
        self.configuration = configuration
        refreshLatestSession()
        if let lastSessionID {
            loadPreview(for: lastSessionID)
        }
    }

    var canStart: Bool {
        process == nil
    }

    var canStop: Bool {
        process != nil
    }

    var canSync: Bool {
        process == nil
            && !isSyncing
            && !isCurrentSessionSynced
            && lastSessionID != nil
            && previewText != "No generated steps yet."
    }

    var menuBarTitle: String {
        switch state {
        case .idle:
            return "Buddy"
        case .starting:
            return "Buddy..."
        case .running:
            return "Buddy REC"
        case .stopping:
            return "Buddy STOP"
        case .error:
            return "Buddy ERR"
        }
    }

    var menuBarSymbolName: String {
        switch state {
        case .idle:
            return "circle.dashed"
        case .starting:
            return "arrow.triangle.2.circlepath"
        case .running:
            return "record.circle"
        case .stopping:
            return "stop.circle"
        case .error:
            return "exclamationmark.triangle"
        }
    }

    func startCapture() {
        guard process == nil else {
            return
        }

        let process = Process()
        let outputPipe = Pipe()
        let errorPipe = Pipe()

        process.currentDirectoryURL = configuration.projectRoot
        process.executableURL = configuration.executableURL
        process.arguments = configuration.arguments
        process.environment = launchEnvironment()
        process.standardOutput = outputPipe
        process.standardError = errorPipe

        outputPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            Task { @MainActor in
                self?.consumeOutput(data)
            }
        }
        errorPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty else {
                return
            }
            Task { @MainActor in
                self?.consumeOutput(data)
            }
        }

        process.terminationHandler = { [weak self] finishedProcess in
            Task { @MainActor in
                self?.handleTermination(process: finishedProcess)
            }
        }

        do {
            try process.run()
            self.process = process
            self.outputPipe = outputPipe
            self.errorPipe = errorPipe
            self.state = .starting
            self.previewText = "No generated steps yet."
            self.isCurrentSessionSynced = false
            self.detailText = "Starting capture. macOS may ask for permissions."
            self.lastLogLine = "Launch command sent."
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
                guard let self, self.process === process, self.state == .starting else {
                    return
                }
                self.state = .running
                self.detailText = "Capture is live."
                self.refreshLatestSession()
            }
        } catch {
            cleanupPipes()
            self.state = .error
            self.detailText = "Could not start tracker."
            self.lastLogLine = error.localizedDescription
        }
    }

    func stopCapture() {
        guard let process else {
            return
        }
        state = .stopping
        detailText = "Stopping and saving the session."
        requestGracefulStop()
        DispatchQueue.main.asyncAfter(deadline: .now() + stopSaveGracePeriod) { [weak self] in
            guard let self, self.process === process else {
                return
            }
            // Python flushes the pending chunk and final pseudocode on shutdown.
            // Give those LLM calls time to persist the last captured screenshots.
            kill(process.processIdentifier, SIGKILL)
        }
    }

    func openDataFolder() {
        NSWorkspace.shared.open(configuration.dataDirectory)
    }

    func openExportsFolder() {
        NSWorkspace.shared.open(configuration.exportsDirectory)
    }

    func revealProjectRoot() {
        NSWorkspace.shared.open(configuration.projectRoot)
    }

    func syncPreviewToInsForge() {
        guard let sessionID = lastSessionID, canSync else {
            return
        }
        isSyncing = true
        detailText = "Syncing approved workflow to InsForge."
        lastLogLine = "Starting InsForge sync."
        let configuration = self.configuration
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let result = Self.runTrackerCommand(
                configuration: configuration,
                arguments: configuration.syncArguments(sessionID: sessionID)
            )
            Task { @MainActor in
                self?.isSyncing = false
                if result.status == 0 {
                    self?.isCurrentSessionSynced = true
                    self?.detailText = "Synced workflow \(sessionID) to InsForge."
                } else {
                    self?.detailText = "InsForge sync failed."
                }
                self?.lastLogLine = result.output.trimmingCharacters(in: .whitespacesAndNewlines)
                self?.updateSyncState(for: sessionID)
            }
        }
    }

    private func consumeOutput(_ data: Data) {
        guard let text = String(data: data, encoding: .utf8) else {
            return
        }
        self.buffer += text
        let parts = self.buffer.components(separatedBy: .newlines)
        self.buffer = parts.last ?? ""
        for line in parts.dropLast() {
            self.handleOutputLine(line)
        }
    }

    private func handleOutputLine(_ rawLine: String) {
        let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !line.isEmpty else {
            return
        }

        lastLogLine = line
        if line.contains("Tracking started.") {
            state = .running
            detailText = "Capture is live."
        }
        if let sessionID = TrackerOutputParser.extractStoppedSessionID(from: line) {
            lastSessionID = sessionID
            loadPreview(for: sessionID)
        }
    }

    private func handleTermination(process: Process) {
        let success = process.terminationStatus == 0 || process.terminationReason == .uncaughtSignal
        if state == .stopping {
            repairLatestSessionIfNeeded()
            refreshLatestSession()
            if let lastSessionID {
                loadPreview(for: lastSessionID)
            }
            state = .idle
            if lastSessionID != nil {
                detailText = "Preview ready. Review before syncing to InsForge."
            } else {
                detailText = "Capture stopped."
            }
        } else if success {
            refreshLatestSession()
            state = .idle
            detailText = "Capture stopped."
        } else {
            state = .error
            detailText = "Tracker exited unexpectedly."
        }

        self.process = nil
        cleanupPipes()
    }

    private func cleanupPipes() {
        outputPipe?.fileHandleForReading.readabilityHandler = nil
        errorPipe?.fileHandleForReading.readabilityHandler = nil
        outputPipe = nil
        errorPipe = nil
        buffer = ""
    }

    private func launchEnvironment() -> [String: String] {
        var environment = ProcessInfo.processInfo.environment
        environment["TRACKER_CONTROL_DIR"] = configuration.controlDirectory.path
        environment["ENABLE_AUDIO_CAPTURE"] = "true"
        if fileManager.fileExists(atPath: "/opt/homebrew/bin/ffmpeg") {
            environment["FFMPEG_PATH"] = "/opt/homebrew/bin/ffmpeg"
        }
        return environment
    }

    private func requestGracefulStop() {
        do {
            try fileManager.createDirectory(
                at: configuration.controlDirectory,
                withIntermediateDirectories: true,
                attributes: nil
            )
            let stopFile = configuration.controlDirectory.appendingPathComponent("stop")
            try Data().write(to: stopFile)
        } catch {
            lastLogLine = "Could not write stop signal: \(error.localizedDescription)"
        }
    }

    private func refreshLatestSession() {
        guard let output = runSQLiteQuery(
            "select id from sessions order by created_at desc limit 1;"
        ) else {
            return
        }
        let sessionID = output.trimmingCharacters(in: .whitespacesAndNewlines)
        if !sessionID.isEmpty {
            lastSessionID = sessionID
            updateSyncState(for: sessionID)
        }
    }

    private func loadPreview(for sessionID: String) {
        let escapedSessionID = sessionID.replacingOccurrences(of: "'", with: "''")
        guard let output = runSQLiteQuery(
            """
            select plain_text
            from final_pseudocode
            where session_id = '\(escapedSessionID)'
            order by created_at desc
            limit 1;
            """
        ) else {
            previewText = "No generated steps yet."
            return
        }
        let trimmed = output.trimmingCharacters(in: .whitespacesAndNewlines)
        previewText = trimmed.isEmpty ? "No generated steps yet." : trimmed
        updateSyncState(for: sessionID)
    }

    private func updateSyncState(for sessionID: String) {
        let escapedSessionID = sessionID.replacingOccurrences(of: "'", with: "''")
        guard let output = runSQLiteQuery(
            """
            select
              (select count(*) from sessions where id = '\(escapedSessionID)' and synced = 0) +
              (select count(*) from chunk_summaries where session_id = '\(escapedSessionID)' and synced = 0) +
              (select count(*) from final_pseudocode where session_id = '\(escapedSessionID)' and synced = 0) +
              (select count(*) from workflow_insights where session_id = '\(escapedSessionID)' and synced = 0) +
              (select count(*) from workflow_templates where session_id = '\(escapedSessionID)' and synced = 0) +
              (select count(*) from workflow_search_index where session_id = '\(escapedSessionID)' and synced = 0) +
              (select count(*) from agent_handoff_queue where session_id = '\(escapedSessionID)' and synced = 0);
            """
        ) else {
            isCurrentSessionSynced = false
            return
        }
        isCurrentSessionSynced = output.trimmingCharacters(in: .whitespacesAndNewlines) == "0"
    }

    private func repairLatestSessionIfNeeded() {
        _ = runSQLiteQuery(
            """
            update sessions
            set status = 'stopped',
                ended_at = coalesce(ended_at, datetime('now'))
            where id = (
              select id from sessions
              where status != 'stopped'
              order by created_at desc
              limit 1
            );
            """
        )
    }

    private func runSQLiteQuery(_ sql: String) -> String? {
        let process = Process()
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/sqlite3")
        process.arguments = [configuration.databaseURL.path, sql]
        process.standardOutput = pipe
        process.standardError = Pipe()

        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            return String(data: data, encoding: .utf8)
        } catch {
            lastLogLine = "SQLite query failed: \(error.localizedDescription)"
            return nil
        }
    }

    private nonisolated static func runTrackerCommand(
        configuration: TrackerLaunchConfiguration,
        arguments: [String]
    ) -> (status: Int32, output: String) {
        let process = Process()
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.currentDirectoryURL = configuration.projectRoot
        process.executableURL = configuration.executableURL
        process.arguments = arguments
        process.environment = ProcessInfo.processInfo.environment
        process.standardOutput = outputPipe
        process.standardError = errorPipe
        do {
            try process.run()
            process.waitUntilExit()
            let output = outputPipe.fileHandleForReading.readDataToEndOfFile()
            let error = errorPipe.fileHandleForReading.readDataToEndOfFile()
            return (
                process.terminationStatus,
                String(data: output + error, encoding: .utf8) ?? ""
            )
        } catch {
            return (1, error.localizedDescription)
        }
    }
}
