"""源码地址安全校验。"""

import posixpath
import re
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from asa_core.domain.projects.entities import SourceType
from asa_core.domain.projects.exceptions import (
    SourceCredentialForbidden,
    SourcePathInvalid,
)

_SCP_LIKE_RE = re.compile(r"^(?P<user>[A-Za-z0-9._-]+)@(?P<host>[A-Za-z0-9.-]+):(?P<path>[^\s]+)$")
_SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "auth",
        "key",
        "password",
        "private_token",
        "signature",
        "token",
    }
)


class SourcePathValidator:
    """校验并规范化本地相对路径或 Git 仓库地址。"""

    @classmethod
    def validate(cls, source_type: str, source_path: str) -> str:
        candidate = source_path.strip()
        if source_type == SourceType.LOCAL:
            return cls._validate_local(candidate)
        if source_type == SourceType.REPOSITORY:
            return cls._validate_repository(candidate)
        raise SourcePathInvalid(source_type, "源码类型必须为 local 或 repository")

    @staticmethod
    def _validate_local(candidate: str) -> str:
        if not candidate:
            raise SourcePathInvalid("local", "本地源码路径不得为空")
        if any(ord(character) < 32 for character in candidate):
            raise SourcePathInvalid("local", "本地源码路径不得包含控制字符")
        if candidate.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", candidate):
            raise SourcePathInvalid("local", "本地源码必须使用授权根目录内的相对路径")

        # 统一分隔符后再规范化，拒绝任何越级路径片段。
        normalized_input = candidate.replace("\\", "/")
        if any(part == ".." for part in normalized_input.split("/")):
            raise SourcePathInvalid("local", "本地源码路径不得包含 ..")
        normalized = posixpath.normpath(normalized_input)
        if normalized in {"", "."} or normalized.startswith("../"):
            raise SourcePathInvalid("local", "本地源码路径无效")
        return normalized

    @classmethod
    def _validate_repository(cls, candidate: str) -> str:
        if not candidate or any(character.isspace() or ord(character) < 32 for character in candidate):
            raise SourcePathInvalid(
                "repository",
                "仓库地址不得为空或包含空白、控制字符",
            )

        scp_match = _SCP_LIKE_RE.fullmatch(candidate)
        if scp_match:
            path = scp_match.group("path")
            if not cls._is_git_path(path):
                raise SourcePathInvalid("repository", "SSH 仓库地址缺少有效仓库路径")
            return candidate

        parsed = urlsplit(candidate)
        if parsed.scheme not in {"https", "ssh"}:
            raise SourcePathInvalid(
                "repository",
                "仓库地址必须使用 HTTPS、SSH 或 git@host:path 格式",
            )
        if not parsed.hostname or not cls._is_git_path(parsed.path):
            raise SourcePathInvalid("repository", "仓库地址缺少有效主机或仓库路径")
        if parsed.password is not None:
            raise SourceCredentialForbidden()
        if parsed.username is not None and (parsed.scheme != "ssh" or parsed.username != "git"):
            raise SourceCredentialForbidden()
        if parsed.fragment:
            raise SourcePathInvalid("repository", "仓库地址不得包含 URL fragment")

        query_keys = {key.lower() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
        if query_keys & _SENSITIVE_QUERY_KEYS:
            raise SourceCredentialForbidden()
        if parsed.query:
            raise SourcePathInvalid("repository", "仓库地址不得包含查询参数")

        # urlsplit().hostname 已移除用户信息；这里保留合法端口并标准化 scheme。
        netloc = f"{parsed.username}@{parsed.hostname}" if parsed.username is not None else parsed.hostname
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((parsed.scheme.lower(), netloc, parsed.path, "", ""))

    @staticmethod
    def _is_git_path(path: str) -> bool:
        normalized = path.strip("/")
        return bool(normalized) and normalized not in {".", ".."} and ".." not in normalized.split("/")
