import Foundation

struct TrackerLaunchConfiguration: Equatable {
    let projectRoot: URL
    let executableURL: URL
    let arguments: [String]
    let dataDirectory: URL
    let exportsDirectory: URL
    let controlDirectory: URL
    let databaseURL: URL

    static func makeDefault(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        sourceFile: String = #filePath
    ) -> TrackerLaunchConfiguration {
        let projectRoot = Self.resolveProjectRoot(environment: environment, sourceFile: sourceFile)
        let venvPython = projectRoot.appendingPathComponent(".venv/bin/python")
        let controlDirectory = projectRoot.appendingPathComponent(".buddybar-control", isDirectory: true)
        let executableURL: URL
        let arguments: [String]

        if let override = environment["TRACKER_PYTHON_EXECUTABLE"], !override.isEmpty {
            executableURL = URL(fileURLWithPath: override)
            arguments = ["-u", "-m", "tracker.cli", "start", "--no-cloud-sync"]
        } else if FileManager.default.fileExists(atPath: venvPython.path) {
            executableURL = venvPython
            arguments = ["-u", "-m", "tracker.cli", "start", "--no-cloud-sync"]
        } else {
            executableURL = URL(fileURLWithPath: "/usr/bin/env")
            arguments = ["python3", "-u", "-m", "tracker.cli", "start", "--no-cloud-sync"]
        }

        return TrackerLaunchConfiguration(
            projectRoot: projectRoot,
            executableURL: executableURL,
            arguments: arguments,
            dataDirectory: projectRoot.appendingPathComponent("data"),
            exportsDirectory: projectRoot.appendingPathComponent("data/exports"),
            controlDirectory: controlDirectory,
            databaseURL: projectRoot.appendingPathComponent("data/local_tracker.db")
        )
    }

    func syncArguments(sessionID: String) -> [String] {
        if executableURL.path == "/usr/bin/env" {
            return [
                "python3", "-u", "-m", "tracker.cli", "sync-summaries",
                "--session-id", sessionID,
            ]
        }
        return ["-u", "-m", "tracker.cli", "sync-summaries", "--session-id", sessionID]
    }

    static func resolveProjectRoot(
        environment: [String: String],
        sourceFile: String
    ) -> URL {
        if let override = environment["TRACKER_PROJECT_ROOT"], !override.isEmpty {
            return URL(fileURLWithPath: override)
        }

        var url = URL(fileURLWithPath: sourceFile)
        for _ in 0..<5 {
            url.deleteLastPathComponent()
        }
        return url
    }
}

enum TrackerOutputParser {
    static func extractStoppedSessionID(from line: String) -> String? {
        let marker = "Session stopped:"
        guard let range = line.range(of: marker) else {
            return nil
        }
        let sessionID = line[range.upperBound...].trimmingCharacters(in: .whitespacesAndNewlines)
        return sessionID.isEmpty ? nil : sessionID
    }
}
