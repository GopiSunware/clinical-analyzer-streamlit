"""Claude sub-agent integration for Clinical Analyzer.

This module reuses the SmartBuild sub-agent pattern to run the locally
authenticated `claude` CLI in sub-agent mode.  We build a prompt that instructs
Claude to analyse clinical context and save answers to a deterministic output
file.  The CLI output is parsed and the saved file is returned to the caller so
Streamlit can surface the response.
"""

from __future__ import annotations

import json
import os
import textwrap
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess


def _now_slug() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%S")


@dataclass
class SubagentResult:
    content: str
    output_path: Path
    files_created: list[str]
    raw_message: str
    job_id: str


class ClaudeSubagentClient:
    """Thin wrapper around the `claude` CLI sub-agent invocation."""

    def __init__(
        self,
        base_dir: str = "subagent_sessions",
        agent_type: str = "technical-documentation",
        response_filename: str = "response.md",
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.agent_type = agent_type
        self.response_filename = response_filename

        # CLI configuration mirrors SmartBuild defaults but can be overridden.
        self.binary = os.getenv("CLAUDE_BINARY", "claude")
        self.model = os.getenv("CLAUDE_SUBAGENT_MODEL", "claude-opus-4-1-20250805")
        extra = os.getenv("CLAUDE_SUBAGENT_EXTRA_ARGS", "")
        self.extra_args = extra.split() if extra else []
        self.timeout = int(os.getenv("CLAUDE_SUBAGENT_TIMEOUT_SEC", "900"))

    # ------------------------------------------------------------------ API --
    def run_question(
        self,
        question: str,
        context_markdown: str,
        context_sources: list[str],
        session_token: Optional[str] = None,
        patient_hint: Optional[str] = None,
    ) -> SubagentResult:
        """Execute a sub-agent task answering ``question`` using the provided context."""
        job_id = f"clinical-{uuid.uuid4().hex[:8]}"
        session_slug = session_token or _now_slug()

        session_dir = self.base_dir / session_slug
        context_dir = session_dir / "context"
        output_dir = session_dir / "output" / job_id
        context_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        context_file = context_dir / f"context-{job_id}.md"
        context_file.write_text(context_markdown, encoding="utf-8")

        prompt = self._build_prompt(
            job_id=job_id,
            question=question,
            context_file=context_file,
            context_sources=context_sources,
            output_dir=output_dir,
            patient_hint=patient_hint,
        )

        provider_result = self._invoke_cli(job_id, prompt, output_dir)

        response_path = output_dir / self.response_filename
        if response_path.exists():
            content = response_path.read_text(encoding="utf-8").strip()
        else:
            # Fall back to raw CLI message so the UI has something useful.
            content = provider_result.get("message", "").strip() or "No response file was created by the sub-agent."

        return SubagentResult(
            content=content,
            output_path=output_dir,
            files_created=provider_result.get("files_created", []),
            raw_message=provider_result.get("message", ""),
            job_id=job_id,
        )

    # ------------------------------------------------------------- Internals --
    def _invoke_cli(self, job_id: str, prompt: str, output_dir: Path) -> Dict[str, Any]:
        command = self._cli_args()
        conversation = self._compose_cli_conversation(prompt)

        env = os.environ.copy()
        env.setdefault("CLAUDE_TELEMETRY_OPTOUT", "1")  # keep logs quiet

        completed = subprocess.run(
            command,
            input=conversation,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            env=env,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited with {completed.returncode}: {completed.stderr.strip() or completed.stdout.strip()}"
            )

        message, raw_json = self._parse_cli_response(completed.stdout)

        if self._is_auth_error(message, raw_json):
            raise RuntimeError(
                "Claude CLI authentication failed. Please run `claude login` on this machine and retry."
            )

        files = self._list_created_files(output_dir)
        return {
            "status": "success",
            "message": message,
            "raw": raw_json,
            "files_created": files,
            "command": command,
        }

    def _cli_args(self) -> list[str]:
        args = [
            self.binary,
            "--print",
            "--output-format",
            "json",
            "--dangerously-skip-permissions",
            "--permission-mode",
            "bypassPermissions",
        ]
        if self.model:
            args += ["--model", self.model]
        if self.extra_args:
            args += self.extra_args
        return args

    def _compose_cli_conversation(self, prompt: str) -> str:
        return textwrap.dedent(
            f"""
            /agents

            Use the {self.agent_type} subagent to complete the following task.

            {prompt}

            Confirm completion with the phrase "TASK COMPLETED".
            """
        ).strip()

    def _build_prompt(
        self,
        job_id: str,
        question: str,
        context_file: Path,
        context_sources: list[str],
        output_dir: Path,
        patient_hint: Optional[str],
    ) -> str:
        context_list = "\n".join(f"- {path}" for path in context_sources)
        patient_line = f"Patient focus: {patient_hint}" if patient_hint else ""

        return textwrap.dedent(
            f"""
            Task ID: {job_id}
            Task Description: Provide a clinical answer to the user's question using the supplied records.
            Output Directory: {output_dir}

            Context artefact:
            - Consolidated notes: {context_file}
            {context_list}

            {patient_line}

            Steps:
            1. Review the consolidated context markdown and any referenced source files.
            2. Answer the user question: "{question}" with clear, concise clinical guidance.
            3. Write the answer to {output_dir / self.response_filename} in Markdown format. Include bullet points where helpful.
            4. Note any assumptions or unavailable data.
            5. Once the file is saved, reply with "TASK COMPLETED".
            """
        ).strip()

    # --------------------------------------------------------------- Helpers --
    @staticmethod
    def _parse_cli_response(stdout: str) -> tuple[str, Optional[Dict[str, Any]]]:
        stdout = stdout.strip()
        if not stdout:
            return "", None
        try:
            data = json.loads(stdout)
            if isinstance(data, dict) and "text" in data:
                text_content = data.get("text")
                if isinstance(text_content, list):
                    message = "\n".join(
                        segment.get("text", "") for segment in text_content if isinstance(segment, dict)
                    )
                else:
                    message = str(text_content)
            else:
                message = json.dumps(data, indent=2)
            return message, data
        except json.JSONDecodeError:
            return stdout, None

    @staticmethod
    def _is_auth_error(message: str, raw_json: Optional[Dict[str, Any]]) -> bool:
        text = (message or "").lower()
        if raw_json and isinstance(raw_json, dict):
            if raw_json.get("is_error"):
                result_text = str(raw_json.get("result", "")).lower()
                if "oauth token has expired" in result_text or "please run /login" in result_text:
                    return True
                if "api error: 401" in result_text:
                    return True
        if "oauth token has expired" in text or "please run /login" in text:
            return True
        if "api error: 401" in text:
            return True
        return False

    @staticmethod
    def _list_created_files(output_dir: Path) -> list[str]:
        files: list[str] = []
        if output_dir.exists():
            for path in output_dir.rglob("*"):
                if path.is_file():
                    files.append(str(path))
        return files


__all__ = ["ClaudeSubagentClient", "SubagentResult"]
