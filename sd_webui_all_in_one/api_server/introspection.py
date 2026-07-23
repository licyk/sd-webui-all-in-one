"""基于真实 Python callable 的 API 参数发现、校验与调用。"""

from __future__ import annotations

import inspect
import types
from collections.abc import Callable, Mapping
from dataclasses import MISSING, dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints


@dataclass(frozen=True, slots=True)
class ParameterInfo:
    """一个公开调用参数的已编译信息。"""

    name: str
    annotation: Any
    required: bool
    default: Any
    description: str
    schema: dict[str, Any]

    def metadata(self) -> dict[str, Any]:
        """返回适合方法发现接口的参数元数据。"""
        result: dict[str, Any] = {
            "name": self.name,
            "type": _display_type(self.annotation),
            "required": self.required,
            "has_default": not self.required,
            "description": self.description,
            "schema": self.schema,
        }
        if not self.required:
            result["default"] = to_json_value(self.default)
        return result


@dataclass(frozen=True, slots=True)
class CallablePlan:
    """真实 callable 的缓存调用计划。"""

    target: Callable[..., Any]
    parameters: tuple[ParameterInfo, ...]
    bound_arguments: Mapping[str, Any]
    injected_parameters: frozenset[str]
    params_schema: dict[str, Any]
    target_name: str
    description: str

    def prepare(self, raw_params: Mapping[str, Any], injections: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """校验并转换 JSON 参数，返回真实 callable 的关键字参数。"""
        known = {parameter.name for parameter in self.parameters}
        unknown = sorted(set(raw_params) - known)
        if unknown:
            raise ValueError(f"Unexpected parameter(s): {', '.join(unknown)}")

        kwargs = dict(self.bound_arguments)
        for parameter in self.parameters:
            if parameter.name in raw_params:
                kwargs[parameter.name] = convert_value(raw_params[parameter.name], parameter.annotation, parameter.name)
            elif parameter.required:
                raise ValueError(f"Missing required parameter: {parameter.name}")
        if injections is not None:
            for name in self.injected_parameters:
                if name not in injections:
                    raise RuntimeError(f"Missing injected parameter: {name}")
                kwargs[name] = injections[name]
        return kwargs

    def invoke(self, raw_params: Mapping[str, Any], injections: Mapping[str, Any]) -> Any:
        """校验并转换 JSON 参数，然后直接调用真实 callable。"""
        kwargs = self.prepare(raw_params, injections)
        return self.target(**kwargs)


def compile_callable(
    target: Callable[..., Any],
    *,
    bound_arguments: Mapping[str, Any] | None = None,
    injected_parameters: frozenset[str] = frozenset(),
    description: str = "",
) -> CallablePlan:
    """从真实 callable 编译调用计划和 JSON Schema。"""
    signature = inspect.signature(target)
    try:
        type_hints = get_type_hints(target, include_extras=True)
    except (NameError, TypeError):
        type_hints = {}
    bound = dict(bound_arguments or {})
    unknown_bound = sorted(set(bound) - set(signature.parameters))
    if unknown_bound:
        raise ValueError(f"Unknown bound parameter(s) for {_callable_name(target)}: {', '.join(unknown_bound)}")
    unknown_injected = sorted(set(injected_parameters) - set(signature.parameters))
    if unknown_injected:
        raise ValueError(f"Unknown injected parameter(s) for {_callable_name(target)}: {', '.join(unknown_injected)}")

    parameter_docs = _parameter_descriptions(target)
    compiled: list[ParameterInfo] = []
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, parameter in signature.parameters.items():
        if name in bound or name in injected_parameters:
            continue
        if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY}:
            raise TypeError(f"Unsupported public parameter kind for {_callable_name(target)}.{name}: {parameter.kind.description}")
        annotation = type_hints.get(name, parameter.annotation)
        if annotation is inspect.Parameter.empty:
            raise TypeError(f"Public parameter must have a type annotation: {_callable_name(target)}.{name}")
        is_required = parameter.default is inspect.Parameter.empty
        schema = schema_for_type(annotation)
        description_text = parameter_docs.get(name, "")
        if description_text:
            schema["description"] = description_text
        if not is_required:
            schema["default"] = to_json_value(parameter.default)
        properties[name] = schema
        if is_required:
            required.append(name)
        compiled.append(
            ParameterInfo(
                name=name,
                annotation=annotation,
                required=is_required,
                default=parameter.default,
                description=description_text,
                schema=schema,
            )
        )

    params_schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        params_schema["required"] = required
    resolved_description = description or _summary(inspect.getdoc(target) or "")
    return CallablePlan(
        target=target,
        parameters=tuple(compiled),
        bound_arguments=bound,
        injected_parameters=injected_parameters,
        params_schema=params_schema,
        target_name=_callable_name(target),
        description=resolved_description,
    )


def schema_for_type(annotation: Any) -> dict[str, Any]:
    """将常用 Python 类型转换成 JSON Schema。"""
    annotation = _unwrap_annotated(annotation)
    if annotation in {Any, object}:
        return {}
    if annotation is None or annotation is type(None):
        return {"type": "null"}
    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is Path:
        return {"type": "string", "format": "path"}
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        values = [member.value for member in annotation]
        return {"type": _json_primitive_type(values[0]) if values else "string", "enum": values}

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        values = list(args)
        schema: dict[str, Any] = {"enum": [to_json_value(value) for value in values]}
        primitive_types = {_json_primitive_type(value) for value in values}
        if len(primitive_types) == 1:
            schema["type"] = primitive_types.pop()
        return schema
    if origin in {Union, types.UnionType}:
        variants = [schema_for_type(item) for item in args]
        primitive_types = [variant.get("type") for variant in variants]
        if all(isinstance(item, str) and set(variant) == {"type"} for item, variant in zip(primitive_types, variants, strict=True)):
            return {"type": primitive_types}
        return {"anyOf": variants}
    if origin is list:
        item_type = args[0] if args else Any
        return {"type": "array", "items": schema_for_type(item_type)}
    if origin is tuple:
        item_type = args[0] if args else Any
        return {"type": "array", "items": schema_for_type(item_type)}
    if origin is dict:
        value_type = args[1] if len(args) == 2 else Any
        return {"type": "object", "additionalProperties": schema_for_type(value_type)}
    if inspect.isclass(annotation) and is_dataclass(annotation):
        properties: dict[str, Any] = {}
        required: list[str] = []
        hints = get_type_hints(annotation, include_extras=True)
        for field_info in fields(annotation):
            field_schema = schema_for_type(hints.get(field_info.name, field_info.type))
            has_default = field_info.default is not MISSING or field_info.default_factory is not MISSING
            if field_info.default is not MISSING:
                field_schema["default"] = to_json_value(field_info.default)
            elif field_info.default_factory is not MISSING:
                field_schema["default"] = to_json_value(field_info.default_factory())
            if not has_default:
                required.append(field_info.name)
            properties[field_info.name] = field_schema
        result: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
        if required:
            result["required"] = required
        return result
    return {}


def convert_value(value: Any, annotation: Any, path: str) -> Any:
    """按类型注解严格转换一个 JSON 值。"""
    annotation = _unwrap_annotated(annotation)
    if annotation in {Any, object}:
        return value
    if annotation is None or annotation is type(None):
        if value is None:
            return None
        raise ValueError(f"Parameter '{path}' must be null")
    if annotation is str:
        if isinstance(value, str):
            return value
        raise ValueError(f"Parameter '{path}' must be a string")
    if annotation is bool:
        if isinstance(value, bool):
            return value
        raise ValueError(f"Parameter '{path}' must be a boolean")
    if annotation is int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        raise ValueError(f"Parameter '{path}' must be an integer")
    if annotation is float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        raise ValueError(f"Parameter '{path}' must be a number")
    if annotation is Path:
        if isinstance(value, str):
            return Path(value)
        raise ValueError(f"Parameter '{path}' must be a path string")
    if inspect.isclass(annotation) and issubclass(annotation, Enum):
        try:
            return annotation(value)
        except ValueError as exc:
            raise ValueError(f"Parameter '{path}' has an invalid enum value") from exc

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        if value in args and any(type(value) is type(candidate) for candidate in args):
            return value
        raise ValueError(f"Parameter '{path}' must be one of: {', '.join(map(repr, args))}")
    if origin in {Union, types.UnionType}:
        for variant in args:
            try:
                return convert_value(value, variant, path)
            except ValueError:
                pass
        raise ValueError(f"Parameter '{path}' does not match any accepted type")
    if origin is list:
        if not isinstance(value, list):
            raise ValueError(f"Parameter '{path}' must be an array")
        item_type = args[0] if args else Any
        return [convert_value(item, item_type, f"{path}[{index}]") for index, item in enumerate(value)]
    if origin is tuple:
        if not isinstance(value, list):
            raise ValueError(f"Parameter '{path}' must be an array")
        item_type = args[0] if args else Any
        return tuple(convert_value(item, item_type, f"{path}[{index}]") for index, item in enumerate(value))
    if origin is dict:
        if not isinstance(value, dict):
            raise ValueError(f"Parameter '{path}' must be an object")
        key_type = args[0] if args else str
        value_type = args[1] if len(args) == 2 else Any
        return {
            convert_value(key, key_type, f"{path}.<key>"): convert_value(item, value_type, f"{path}.{key}")
            for key, item in value.items()
        }
    if inspect.isclass(annotation) and is_dataclass(annotation):
        if not isinstance(value, dict):
            raise ValueError(f"Parameter '{path}' must be an object")
        hints = get_type_hints(annotation, include_extras=True)
        known = {field_info.name for field_info in fields(annotation)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ValueError(f"Unexpected field(s) in '{path}': {', '.join(unknown)}")
        kwargs: dict[str, Any] = {}
        for field_info in fields(annotation):
            if field_info.name in value:
                kwargs[field_info.name] = convert_value(value[field_info.name], hints.get(field_info.name, field_info.type), f"{path}.{field_info.name}")
            elif field_info.default is MISSING and field_info.default_factory is MISSING:
                raise ValueError(f"Missing required field: {path}.{field_info.name}")
        return annotation(**kwargs)
    return value


def to_json_value(value: Any) -> Any:
    """将默认值或调用结果递归转换为 JSON 可序列化值。"""
    if value is inspect.Parameter.empty:
        return None
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Enum):
        return to_json_value(value.value)
    if is_dataclass(value) and not isinstance(value, type):
        return {field_info.name: to_json_value(getattr(value, field_info.name)) for field_info in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _unwrap_annotated(annotation: Any) -> Any:
    return get_args(annotation)[0] if get_origin(annotation) is Annotated else annotation


def _display_type(annotation: Any) -> Any:
    schema = schema_for_type(annotation)
    if "type" in schema:
        return schema["type"]
    if "anyOf" in schema:
        return [variant.get("type", "any") for variant in schema["anyOf"]]
    return "any"


def _json_primitive_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


def _callable_name(target: Callable[..., Any]) -> str:
    module = getattr(target, "__module__", target.__class__.__module__)
    qualname = getattr(target, "__qualname__", target.__class__.__qualname__)
    return f"{module}.{qualname}"


def _summary(docstring: str) -> str:
    return docstring.strip().split("\n\n", 1)[0].replace("\n", " ").strip()


def _parameter_descriptions(target: Callable[..., Any]) -> dict[str, str]:
    lines = (inspect.getdoc(target) or "").splitlines()
    descriptions: dict[str, str] = {}
    in_args = False
    current_name: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped in {"Args:", "Arguments:", "Parameters:"}:
            in_args = True
            current_name = None
            continue
        if not in_args:
            continue
        if stripped.endswith(":") and not line.startswith((" ", "\t")):
            break
        if not stripped:
            continue
        if ":" in stripped:
            prefix, text = stripped.split(":", 1)
            name = prefix.split("(", 1)[0].strip()
            if name.isidentifier():
                current_name = name
                descriptions[name] = text.strip()
                continue
        if current_name:
            descriptions[current_name] = f"{descriptions[current_name]} {stripped}".strip()
    return descriptions
