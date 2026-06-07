import AppKit
import SwiftUI

final class BuddyBarAppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        false
    }
}

@main
struct BuddyBarApp: App {
    @NSApplicationDelegateAdaptor(BuddyBarAppDelegate.self) private var appDelegate
    @StateObject private var controller = TrackerProcessController()

    var body: some Scene {
        Window("BuddyBar", id: "buddy-panel") {
            BuddyPanelView(controller: controller)
        }
        .defaultSize(width: 380, height: 560)
        .windowResizability(.contentSize)

        MenuBarExtra(controller.menuBarTitle, systemImage: controller.menuBarSymbolName) {
            BuddyPanelView(controller: controller)
        }
        .menuBarExtraStyle(.window)
    }
}

private struct BuddyPanelView: View {
    @ObservedObject var controller: TrackerProcessController

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            VStack(alignment: .leading, spacing: 6) {
                Text("Screen Buddy")
                    .font(.system(size: 16, weight: .semibold))
                Text(controller.detailText)
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 8) {
                Button(action: controller.startCapture) {
                    Label("Start", systemImage: "record.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!controller.canStart)
                .keyboardShortcut("r")

                Button(action: controller.stopCapture) {
                    Label("Stop", systemImage: "stop.circle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .disabled(!controller.canStop)
                .keyboardShortcut(".")
            }

            VStack(alignment: .leading, spacing: 8) {
                statusRow(title: "State", value: controller.state.rawValue.capitalized)
                statusRow(title: "Session", value: controller.lastSessionID ?? "None yet")
                statusRow(title: "Project", value: controller.configuration.projectRoot.lastPathComponent)
                statusRow(title: "Last Log", value: controller.lastLogLine)
            }
            .font(.system(size: 12))

            Divider()

            VStack(alignment: .leading, spacing: 8) {
                Text("Generated Steps Preview")
                    .font(.system(size: 12, weight: .semibold))
                ScrollView {
                    Text(controller.previewText)
                        .font(.system(size: 12))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .frame(height: 180)
                .padding(8)
                .background(Color(nsColor: .textBackgroundColor))
                .clipShape(RoundedRectangle(cornerRadius: 8))

                Button(action: controller.syncPreviewToInsForge) {
                    Label(
                        syncButtonTitle,
                        systemImage: "icloud.and.arrow.up"
                    )
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(!controller.canSync)
            }

            Divider()

            VStack(alignment: .leading, spacing: 8) {
                Button("Open Data Folder", action: controller.openDataFolder)
                    .keyboardShortcut("d")
                Button("Open Exports Folder", action: controller.openExportsFolder)
                    .keyboardShortcut("e")
                Button("Reveal Project Root", action: controller.revealProjectRoot)
                Button("Quit Buddy") {
                    if controller.canStop {
                        controller.stopCapture()
                    }
                    NSApp.terminate(nil)
                }
                .keyboardShortcut("q")
            }
            .buttonStyle(.plain)
            .font(.system(size: 12))

            Text("First run needs Screen Recording and Accessibility permissions in macOS Settings.")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(16)
        .frame(width: 380)
    }

    private var syncButtonTitle: String {
        if controller.isSyncing {
            return "Syncing..."
        }
        if controller.isCurrentSessionSynced {
            return "Already Synced to InsForge"
        }
        return "Sync Preview to InsForge"
    }

    @ViewBuilder
    private func statusRow(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(.secondary)
            Text(value)
                .lineLimit(2)
                .textSelection(.enabled)
        }
    }
}
