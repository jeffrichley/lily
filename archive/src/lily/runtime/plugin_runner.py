"""Containerized plugin runner using Docker Python SDK."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from textwrap import dedent
from typing import Any

import docker
from docker.models.containers import Container

from lily.config import SkillSandboxSettings
from lily.skills.types import SkillEntry


class PluginRuntimeError(RuntimeError):
    """Deterministic runtime failure from plugin container execution."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> None:
        """Store deterministic plugin runtime error payload.

        Args:
            code: Deterministic machine-readable error code.
            message: Human-readable error message.
            data: Optional structured error payload.
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or {}


class DockerPluginRunner:
    """Run plugin entrypoints in container-only sandbox."""

    def __init__(self, *, sandbox: SkillSandboxSettings) -> None:
        """Store immutable sandbox settings.

        Args:
            sandbox: Global sandbox execution settings.
        """
        self._sandbox = sandbox

    def run(
        self,
        *,
        entry: SkillEntry,
        user_text: str,
        security_hash: str,
        agent_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Execute one plugin call in container and return typed payload.

        Args:
            entry: Plugin skill entry.
            user_text: Raw user payload.
            security_hash: Approved security hash.
            agent_id: Active agent id.
            session_id: Active session id.

        Returns:
            Response payload emitted by plugin.

        Raises:
            PluginRuntimeError: If container runtime is unavailable or fails.
        """
        client = self._docker_client()
        with (
            tempfile.TemporaryDirectory(prefix="lily-plugin-input-") as input_dir,
            tempfile.TemporaryDirectory(prefix="lily-plugin-output-") as output_dir,
        ):
            entrypoint = entry.plugin.entrypoint
            if entrypoint is None:
                raise PluginRuntimeError(
                    code="plugin_contract_invalid",
                    message="Error: plugin entrypoint is missing.",
                )
            input_path = Path(input_dir)
            output_path = Path(output_dir)
            request_payload = {
                "contract_version": "v1",
                "skill_name": entry.name,
                "agent_id": agent_id,
                "session_id": session_id,
                "security_hash": security_hash,
                "payload": user_text,
                "entrypoint": entrypoint,
            }
            self._prepare_input(
                entry=entry,
                request_payload=request_payload,
                input_path=input_path,
            )
            container = self._start_container(
                client=client,
                input_path=input_path,
                output_path=output_path,
                env_allowlist=entry.plugin.env_allowlist,
            )
            return self._await_result(container=container, output_path=output_path)

    @staticmethod
    def _docker_client() -> docker.DockerClient:
        """Build docker SDK client or raise deterministic error.

        Returns:
            Ready Docker SDK client.

        Raises:
            PluginRuntimeError: If daemon is unavailable.
        """
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception as exc:  # pragma: no cover - environment dependent
            raise PluginRuntimeError(
                code="plugin_container_unavailable",
                message="Error: docker daemon is unavailable for plugin runtime.",
            ) from exc

    def _prepare_input(
        self,
        *,
        entry: SkillEntry,
        request_payload: dict[str, str],
        input_path: Path,
    ) -> None:
        """Write request envelope and plugin bundle into container input mount.

        Args:
            entry: Skill entry containing plugin source root.
            request_payload: Serialized plugin request envelope.
            input_path: Host path mounted at `/input`.
        """
        skill_root = entry.path.parent
        bundle_root = input_path / "skill"
        shutil.copytree(skill_root, bundle_root)
        (input_path / "request.json").write_text(
            json.dumps(request_payload, sort_keys=True),
            encoding="utf-8",
        )
        (input_path / "runner.py").write_text(_RUNNER_SCRIPT, encoding="utf-8")

    def _start_container(
        self,
        *,
        client: docker.DockerClient,
        input_path: Path,
        output_path: Path,
        env_allowlist: tuple[str, ...],
    ) -> Container:
        """Start one sandboxed container using Docker SDK.

        Args:
            client: Docker SDK client.
            input_path: Input mount host path.
            output_path: Output mount host path.
            env_allowlist: Environment variable allowlist for container env.

        Returns:
            Started container handle.

        Raises:
            PluginRuntimeError: If container startup fails.
        """
        volumes = {
            str(input_path): {"bind": "/input", "mode": "ro"},
            str(output_path): {"bind": "/output", "mode": "rw"},
        }
        env = {
            name: os.environ[name]
            for name in sorted(set(env_allowlist))
            if name in os.environ
        }
        try:
            return client.containers.run(
                image=self._sandbox.image,
                command=["python", "/input/runner.py"],
                detach=True,
                remove=True,
                network_disabled=True,
                read_only=True,
                user=self._sandbox.non_root_user,
                mem_limit=f"{self._sandbox.memory_mb}m",
                nano_cpus=int(self._sandbox.cpu_cores * 1_000_000_000),
                working_dir="/input",
                volumes=volumes,
                environment=env,
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            raise PluginRuntimeError(
                code="plugin_container_unavailable",
                message="Error: failed to start plugin sandbox container.",
            ) from exc

    def _await_result(
        self, *, container: Container, output_path: Path
    ) -> dict[str, Any]:
        """Wait for container completion and parse plugin response.

        Args:
            container: Running container handle.
            output_path: Output mount host path.

        Returns:
            Parsed plugin response mapping.

        Raises:
            PluginRuntimeError: If runtime times out or payload is invalid.
        """
        try:
            result = container.wait(timeout=self._sandbox.timeout_seconds)
        except Exception as exc:  # pragma: no cover - environment dependent
            with suppress(Exception):
                container.kill()
            raise PluginRuntimeError(
                code="plugin_timeout",
                message="Error: plugin container timed out.",
            ) from exc

        status_code = int(result.get("StatusCode", 1))
        response_file = output_path / "response.json"
        logs = container.logs(stdout=True, stderr=True)[: self._sandbox.logs_max_bytes]
        if status_code != 0:
            raise PluginRuntimeError(
                code="plugin_runtime_failed",
                message="Error: plugin container failed.",
                data={
                    "status_code": status_code,
                    "logs": logs.decode(errors="replace"),
                },
            )
        if not response_file.exists():
            raise PluginRuntimeError(
                code="plugin_runtime_failed",
                message="Error: plugin container produced no response payload.",
            )
        try:
            payload = json.loads(response_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PluginRuntimeError(
                code="plugin_runtime_failed",
                message="Error: plugin response payload is invalid JSON.",
            ) from exc
        if not isinstance(payload, dict):
            raise PluginRuntimeError(
                code="plugin_runtime_failed",
                message="Error: plugin response payload must be a JSON object.",
            )
        return payload


_RUNNER_SCRIPT = dedent(
    """
    import importlib.util
    import json
    from pathlib import Path

    request = json.loads(Path("/input/request.json").read_text(encoding="utf-8"))
    entrypoint = request["entrypoint"]
    payload = request["payload"]
    skill_name = request["skill_name"]
    agent_id = request["agent_id"]
    session_id = request["session_id"]
    module_path = Path("/input/skill") / entrypoint

    spec = importlib.util.spec_from_file_location("lily_plugin_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("invalid plugin module spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "run"):
        raise RuntimeError("plugin entrypoint must expose run(...)")
    result = module.run(
        payload,
        session_id=session_id,
        agent_id=agent_id,
        skill_name=skill_name,
    )
    if not isinstance(result, dict):
        raise RuntimeError("plugin run(...) must return dict")
    Path("/output/response.json").write_text(json.dumps(result), encoding="utf-8")
    """
).strip()
