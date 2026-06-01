/**
 * Safe Shell Command Tool
 *
 * Provides a custom `safe_shell` tool that runs shell commands with
 * safety controls: allowlists, blocklists, timeouts, and output truncation.
 *
 * Designed for common dev tasks:
 *   - install dependencies (npm, yarn, pnpm, pip, etc.)
 *   - run tests (pytest, jest, vitest, mocha, etc.)
 *   - start dev servers (npm start, yarn dev, pnpm dev, etc.)
 *   - lint / format code (eslint, prettier, black, ruff, etc.)
 *
 * Safety features:
 *   - Blocklist of dangerous commands (rm -rf, sudo, dd, mkfs, etc.)
 *   - Allowlist mode for extra-safe environments
 *   - Configurable timeout per command
 *   - Output truncation (default 1000 lines)
 *   - Interactive confirmation for risky commands
 */

import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { exec } from "node:child_process";
import { promisify } from "node:util";
import { homedir } from "node:os";

const execAsync = promisify(exec);

// ── Configuration ──────────────────────────────────────────────────────────

interface SafeShellConfig {
  /** Max output lines before truncation (default: 1000). 0 = no limit. */
  maxOutputLines?: number;
  /** Default timeout in seconds (default: 300 = 5 min). */
  defaultTimeout?: number;
  /** Require confirmation for commands matching these patterns. */
  requireConfirm?: string[];
  /** Allowlist: if set, only commands matching these prefixes are allowed. */
  allowlist?: string[];
  /** Blocklist: commands/patterns that are always denied. */
  blocklist?: string[];
}

const DEFAULT_CONFIG: SafeShellConfig = {
  maxOutputLines: 1000,
  defaultTimeout: 300,
  requireConfirm: ["sudo", "chmod", "chown", "apt", "yum", "dnf", "pacman", "brew uninstall", "rm -rf", "rm -r"],
  allowlist: [],
  blocklist: [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    "wget http.*>|",
    "curl.*>|",
    "> /dev/sd",
    "chmod 777",
    "chown root",
    "sudo rm",
    "sudo dd",
    "sudo mkfs",
    ":(){:|:&};:",
    "exec",
  ],
};

// ── Helpers ────────────────────────────────────────────────────────────────

function normalizePath(p: string): string {
  return p.replace(/^~(?=$|\/|\\)/, homedir());
}

function checkBlocklist(command: string, blocklist: string[]): string | null {
  for (const pattern of blocklist) {
    if (command.includes(pattern)) {
      return `Blocked by blocklist: contains "${pattern}"`;
    }
  }
  return null;
}

function checkAllowlist(command: string, allowlist: string[]): boolean {
  if (allowlist.length === 0) return true;
  return allowlist.some((prefix) => command.startsWith(prefix));
}

function checkConfirm(command: string, requireConfirm: string[]): boolean {
  return requireConfirm.some((pattern) => command.includes(pattern));
}

function truncateOutput(output: string, maxLines: number): { text: string; truncated: boolean } {
  if (maxLines <= 0 || output.split("\n").length <= maxLines) {
    return { text: output, truncated: false };
  }
  const lines = output.split("\n");
  const head = lines.slice(0, Math.floor(maxLines / 2));
  const tail = lines.slice(-Math.floor(maxLines / 2));
  const dropped = lines.length - head.length - tail.length;
  return {
    text: `${head.join("\n")}\n... [truncated ${dropped} lines, set maxOutputLines to increase] ...\n${tail.join("\n")}`,
    truncated: true,
  };
}

// ── Extension ──────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  const config: SafeShellConfig = { ...DEFAULT_CONFIG };

  pi.registerTool({
    name: "safe_shell",
    label: "Safe Shell",
    description:
      "Execute a shell command safely. Supports dependency installs, test runs, dev servers, linting, and formatting. " +
      "Has built-in safety: blocklist (dangerous commands), allowlist (optional lock-down), timeout, and output truncation. " +
      "Use for: npm install, pip install, pytest, jest, eslint, prettier, tsc, etc.",
    promptSnippet: "Run shell commands safely for installs, tests, dev servers, lint/format",
    promptGuidelines: [
      "Use safe_shell for running dev commands (install, test, lint, format, start dev server).",
      "For one-off quick checks, use the bash tool instead.",
      "safe_shell requires confirmation for risky commands (sudo, chmod, rm -rf, package managers).",
    ],
    parameters: Type.Object({
      command: Type.String({
        description:
          "The shell command to execute. Examples: 'npm install', 'pytest tests/', 'eslint src/', 'prettier --write src/'.",
      }),
      timeout: Type.Optional(
        Type.Number({
          description: "Timeout in seconds (default: 300). Set lower for quick commands, higher for installs.",
        }),
      ),
      maxOutputLines: Type.Optional(
        Type.Number({
          description: "Max output lines before truncation (default: 1000). 0 = no limit.",
        }),
      ),
      confirm: Type.Optional(
        Type.Boolean({
          description:
            "Set true to skip confirmation prompt (use only after reviewing the command). Default: false.",
        }),
      ),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const command = params.command.trim();
      const timeout = (params.timeout ?? config.defaultTimeout) * 1000;
      const maxLines = params.maxOutputLines ?? config.maxOutputLines;

      // Resolve ~ in paths
      const resolvedCommand = normalizePath(command);

      // Check blocklist
      const blockReason = checkBlocklist(resolvedCommand, config.blocklist);
      if (blockReason) {
        return {
          content: [{ type: "text", text: `❌ ${blockReason}` }],
          details: { isError: true },
        };
      }

      // Check allowlist (if configured)
      if (!checkAllowlist(resolvedCommand, config.allowlist)) {
        return {
          content: [
            {
              type: "text",
              text: `❌ Command not in allowlist. Allowed prefixes: ${config.allowlist.join(", ") || "none (allowlist mode active)"}`,
            },
          ],
          details: { isError: true },
        };
      }

      // Check if confirmation is needed
      if (checkConfirm(resolvedCommand, config.requireConfirm) && !params.confirm) {
        const confirmed = await ctx.ui.confirm(
          "⚠️  Confirm Command",
          `Run this command?\n\n\`\`\`bash\n${resolvedCommand}\n\`\`\`\n\nTimeout: ${timeout / 1000}s`,
        );
        if (!confirmed) {
          return {
            content: [{ type: "text", text: "⛔ Command cancelled by user." }],
            details: { isError: false },
          };
        }
      }

      // Execute
      try {
        ctx.ui.setStatus("safe_shell", `Running: ${resolvedCommand.slice(0, 60)}${resolvedCommand.length > 60 ? "..." : ""}`);

        const { stdout, stderr } = await execAsync(resolvedCommand, {
          cwd: ctx.cwd,
          timeout,
          signal,
        });

        const combined = stdout + (stderr ? `\n${stderr}` : "");
        const result = truncateOutput(combined, maxLines);

        ctx.ui.setStatus("safe_shell", "✓ done");

        return {
          content: [
            {
              type: "text",
              text: [
                `✅ Command completed successfully.`,
                `📁 Working directory: ${ctx.cwd}`,
                `⏱ Duration: ${timeout / 1000}s timeout`,
                result.truncated ? `⚠️ Output truncated (${result.text.split("\n").length} lines shown)` : "",
                `--- Output ---`,
                result.text,
              ].filter(Boolean).join("\n"),
            },
          ],
          details: {
            command: resolvedCommand,
            exitCode: 0,
            truncated: result.truncated,
          },
        };
      } catch (error: unknown) {
        const err = error as { stdout?: string; stderr?: string; code?: number; signal?: string };
        const stderr = err.stderr || String(error);
        const result = truncateOutput(stderr, maxLines);

        ctx.ui.setStatus("safe_shell", "✗ error");

        return {
          content: [
            {
              type: "text",
              text: [
                `❌ Command failed (exit code: ${err.code ?? "unknown"}).`,
                `📁 Working directory: ${ctx.cwd}`,
                `--- Error Output ---`,
                result.text,
              ].filter(Boolean).join("\n"),
            },
          ],
          details: {
            command: resolvedCommand,
            exitCode: err.code ?? 1,
            truncated: result.truncated,
            isError: true,
          },
        };
      }
    },
  });
}
