"""Deterministic XAML authoring + validation tools for classic RPA.

These tools let the agent skip the most failure-prone part of building a
UiPath RPA project: generating byte-exact, schema-valid XAML from a small
structured spec. The agent describes *what* the workflow should do in a
typed record form; the renderer produces XAML that satisfies every rule in
``skills/skills/uipath-rpa/references/xaml/xaml-basics-and-rules.md`` and
``.../common-pitfalls.md``.

Design choice: we intentionally use ``xml.etree.ElementTree`` rather than a
Jinja template library. XAML's escaping rules mix attribute-context (quotes
become ``&quot;``) with element-text context (``<`` inside C# generics
becomes ``&lt;``), and those are the exact rules ``ElementTree`` handles
for free. Templates would either duplicate them or get them subtly wrong.

Exposed tools (see ``get_xaml_tools`` at the bottom):

- ``create_xaml_workflow`` — render a whole XAML workflow from a spec,
  write it to ``project_dir/relative_path``, run ``validate_xaml`` on it.
- ``validate_xaml`` — lint any XAML file on disk and return precise,
  actionable errors (line numbers + DisplayName + one-line fix hint).
"""
from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from uipath_claude.tools._result import ToolOutcome

__all__ = [
    "create_xaml_workflow",
    "validate_xaml",
    "get_xaml_tools",
    "render_xaml_workflow",
    "XamlRenderError",
    "XamlValidationIssue",
]


# -----------------------------------------------------------------------------
# XAML namespaces
# -----------------------------------------------------------------------------

_NS_ACTIVITIES = "http://schemas.microsoft.com/netfx/2009/xaml/activities"
_NS_X = "http://schemas.microsoft.com/winfx/2006/xaml"
_NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_NS_SAP = "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
_NS_SAP2010 = "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
_NS_SADS = "http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger"
_NS_SCG = "clr-namespace:System.Collections.Generic;assembly=System.Private.CoreLib"
_NS_SCO = "clr-namespace:System.Collections.ObjectModel;assembly=System.Private.CoreLib"
_NS_UI = "http://schemas.uipath.com/workflow/activities"
_NS_SYS = "clr-namespace:System;assembly=System.Private.CoreLib"
_NS_IO = "clr-namespace:System.IO;assembly=System.Private.CoreLib"

# ElementTree prefixes. ``ET`` renders these in the root element.
_PREFIXES = {
    "x": _NS_X,
    "mc": _NS_MC,
    "sap": _NS_SAP,
    "sap2010": _NS_SAP2010,
    "sads": _NS_SADS,
    "scg": _NS_SCG,
    "sco": _NS_SCO,
    "s": _NS_SYS,
    "io": _NS_IO,
    "ui": _NS_UI,
}

_DEFAULT_CSHARP_NAMESPACES = (
    "System",
    "System.Activities",
    "System.Activities.Statements",
    "System.Collections.Generic",
    "System.IO",
    "System.Linq",
    "System.Text.RegularExpressions",
    "UiPath.Core",
    "UiPath.Core.Activities",
)

_DEFAULT_REFERENCES = (
    "System.Activities",
    "System.Private.CoreLib",
    "UiPath.System.Activities",
)


# -----------------------------------------------------------------------------
# Errors and results
# -----------------------------------------------------------------------------


class XamlRenderError(ValueError):
    """Raised when the structured spec is malformed.

    These are *never* raised because of XAML escaping — that path is
    guaranteed by ``ElementTree``. They are raised when the agent
    passes e.g. an activity without a required field, or an argument
    spec with a disallowed direction.
    """


@dataclass(frozen=True)
class XamlValidationIssue:
    level: str          # "error" | "warning"
    line: int | None
    col: int | None
    message: str
    fix: str


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _qname(prefix: str, local: str) -> str:
    """Return ``{ns}local`` as expected by ``ET``."""
    ns = _PREFIXES[prefix] if prefix else _NS_ACTIVITIES
    return f"{{{ns}}}{local}"


def _set_x_attr(el: ET.Element, local: str, value: str) -> None:
    el.set(_qname("x", local), value)


def _set_sap2010_attr(el: ET.Element, local: str, value: str) -> None:
    el.set(_qname("sap2010", local), value)


_ID_COUNTER: dict[str, int] = {}


def _next_id(kind: str) -> str:
    """Stable, sequential ``WorkflowViewState.IdRef`` per activity kind."""
    _ID_COUNTER[kind] = _ID_COUNTER.get(kind, 0) + 1
    return f"{kind}_{_ID_COUNTER[kind]}"


def _reset_ids() -> None:
    _ID_COUNTER.clear()


def _derive_x_class(relative_path: str) -> str:
    """Convert ``Workflows/ExtractInvoice.xaml`` -> ``Workflows_ExtractInvoice``."""
    p = relative_path.replace("\\", "/")
    if p.lower().endswith(".xaml"):
        p = p[:-5]
    return re.sub(r"[^A-Za-z0-9_]", "_", p)


_ARG_PREFIX_RE = re.compile(r"^(in_|out_|io_)[A-Za-z][A-Za-z0-9_]*$")
_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_DIRECTION_TO_ARG = {
    "In": "InArgument",
    "Out": "OutArgument",
    "InOut": "InOutArgument",
}


def _validate_spec_arg(arg: dict) -> None:
    name = str(arg.get("name", "")).strip()
    direction = str(arg.get("direction", "")).strip()
    type_ = str(arg.get("type", "")).strip()
    if not name or not _ARG_PREFIX_RE.match(name):
        raise XamlRenderError(
            f"Argument name '{name}' must match UiPath convention: "
            "start with 'in_' / 'out_' / 'io_' followed by a PascalCase "
            "identifier (e.g. 'in_FilePath')."
        )
    if direction not in _DIRECTION_TO_ARG:
        raise XamlRenderError(
            f"Argument '{name}' has invalid direction '{direction}'. "
            "Must be one of: In, Out, InOut."
        )
    if not type_:
        raise XamlRenderError(
            f"Argument '{name}' is missing 'type' (e.g. 'x:String' or "
            "'scg:Dictionary(x:String, x:String)')."
        )


def _normalize_variable_type(type_: str) -> str:
    """Map common agent mistakes to XAML-safe type names."""
    t = str(type_ or "").strip()
    low = t.lower().replace(" ", "")
    if low in ("x:string[]", "string[]", "system.string[]", "str[]"):
        return "s:String[]"
    return t


def _normalize_catch_type(exc_type: str) -> str:
    """Use clr-prefixed System types so Catch resolves under System.Private.CoreLib."""
    t = str(exc_type or "").strip() or "System.Exception"
    if t in ("System.Exception", "Exception"):
        return "s:Exception"
    if t.startswith("System.") and "." not in t[7:]:
        return "s:" + t.split(".", 1)[1]
    return t


def _validate_spec_var(var: dict) -> None:
    name = str(var.get("name", "")).strip()
    type_ = str(var.get("type", "")).strip()
    if not name or not _VAR_NAME_RE.match(name):
        raise XamlRenderError(
            f"Variable name '{name}' must be a plain identifier."
        )
    if not type_:
        raise XamlRenderError(f"Variable '{name}' is missing 'type'.")


# -----------------------------------------------------------------------------
# Activity emitters
# -----------------------------------------------------------------------------
#
# Each emitter takes ``(parent, spec)`` and appends exactly one activity
# element to ``parent``. Expressions passed in by the agent are wrapped in
# square brackets where UiPath expects them. The ElementTree layer escapes
# any ``<`` / ``>`` / ``&`` inside expressions automatically, so the agent
# never has to deal with XML escaping.


def _wrap_expr(expr: str) -> str:
    """Wrap a user expression in ``[…]`` if not already wrapped."""
    s = str(expr or "").strip()
    if not s:
        return ""
    if s.startswith("[") and s.endswith("]"):
        return s
    return f"[{s}]"


def _emit_arg_element(parent: ET.Element, tag_prefix: str, type_args: str, expr: str) -> ET.Element:
    """Emit ``<InArgument x:TypeArguments="x:String">[expr]</InArgument>`` etc."""
    el = ET.SubElement(parent, tag_prefix)
    _set_x_attr(el, "TypeArguments", type_args)
    el.text = _wrap_expr(expr)
    return el


def _emit_log_message(parent: ET.Element, spec: dict) -> None:
    level = str(spec.get("level", "Info"))
    message_expr = spec.get("message_expr") or spec.get("message")
    if not message_expr:
        raise XamlRenderError("LogMessage requires 'message_expr' or 'message'.")
    el = ET.SubElement(parent, _qname("ui", "LogMessage"))
    el.set("DisplayName", spec.get("display_name", f"Log ({level})"))
    el.set("Level", level)
    el.set("Message", _wrap_expr(message_expr))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("LogMessage"))


def _emit_write_line(parent: ET.Element, spec: dict) -> None:
    text_expr = spec.get("text_expr") or spec.get("text")
    if not text_expr:
        raise XamlRenderError("WriteLine requires 'text_expr' or 'text'.")
    el = ET.SubElement(parent, "WriteLine")
    el.set("DisplayName", spec.get("display_name", "Write Line"))
    el.set("Text", _wrap_expr(text_expr))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("WriteLine"))


def _emit_assign(parent: ET.Element, spec: dict) -> None:
    to = str(spec.get("to", "")).strip()
    value_expr = spec.get("value_expr") or spec.get("value")
    if not to:
        raise XamlRenderError("Assign requires 'to' (target variable / argument name).")
    if value_expr is None:
        raise XamlRenderError(f"Assign to '{to}' requires 'value_expr'.")
    to_type = str(spec.get("to_type", "x:String")).strip() or "x:String"
    to_direction = str(spec.get("to_direction", "Out")).strip()
    if to_direction not in _DIRECTION_TO_ARG:
        raise XamlRenderError(
            f"Assign 'to_direction' must be In/Out/InOut, got {to_direction!r}."
        )
    assign = ET.SubElement(parent, "Assign")
    assign.set("DisplayName", spec.get("display_name", f"Assign {to}"))
    _set_sap2010_attr(assign, "WorkflowViewState.IdRef", _next_id("Assign"))
    assign_to = ET.SubElement(assign, "Assign.To")
    _emit_arg_element(assign_to, _DIRECTION_TO_ARG[to_direction], to_type, f"[{to}]")
    assign_val = ET.SubElement(assign, "Assign.Value")
    _emit_arg_element(assign_val, "InArgument", to_type, str(value_expr))


def _emit_body(parent: ET.Element, body: list[dict]) -> None:
    for entry in body or []:
        kind = entry.get("kind")
        emitter = _EMITTERS.get(kind)
        if emitter is None:
            raise XamlRenderError(
                f"Unknown activity kind '{kind}'. Supported kinds: "
                + ", ".join(sorted(_EMITTERS))
            )
        emitter(parent, entry)


def _emit_sequence(parent: ET.Element, spec: dict) -> None:
    seq = ET.SubElement(parent, "Sequence")
    seq.set("DisplayName", spec.get("display_name", "Sequence"))
    _set_sap2010_attr(seq, "WorkflowViewState.IdRef", _next_id("Sequence"))
    variables = spec.get("variables") or []
    if variables:
        vars_el = ET.SubElement(seq, "Sequence.Variables")
        for v in variables:
            _validate_spec_var(v)
            var_el = ET.SubElement(vars_el, "Variable")
            _set_x_attr(var_el, "TypeArguments", _normalize_variable_type(v["type"]))
            var_el.set("Name", v["name"])
            if "default" in v and v["default"] is not None:
                var_el.set("Default", _wrap_expr(str(v["default"])))
    _emit_body(seq, spec.get("body") or [])


def _emit_if(parent: ET.Element, spec: dict) -> None:
    cond = spec.get("condition_expr") or spec.get("condition")
    if not cond:
        raise XamlRenderError("If requires 'condition_expr'.")
    el = ET.SubElement(parent, "If")
    el.set("DisplayName", spec.get("display_name", "If"))
    # Use If.Condition element (not the Condition attribute): expressions often
    # contain ``<`` / ``>`` which are illegal inside XML attribute values unless
    # escaped; element text is escaped correctly by ElementTree.
    cond_el = ET.SubElement(el, "If.Condition")
    in_arg = ET.SubElement(cond_el, "InArgument")
    _set_x_attr(in_arg, "TypeArguments", "x:Boolean")
    in_arg.text = _wrap_expr(cond)
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("If"))
    then_body = spec.get("then") or []
    else_body = spec.get("else") or []
    if then_body:
        then_el = ET.SubElement(el, "If.Then")
        # If exactly one activity in Then, emit it directly (Studio idiom);
        # otherwise wrap in a Sequence for readability.
        if len(then_body) == 1:
            _emit_body(then_el, then_body)
        else:
            _emit_sequence(then_el, {"body": then_body, "display_name": "Then"})
    if else_body:
        else_el = ET.SubElement(el, "If.Else")
        if len(else_body) == 1:
            _emit_body(else_el, else_body)
        else:
            _emit_sequence(else_el, {"body": else_body, "display_name": "Else"})


def _emit_while(parent: ET.Element, spec: dict) -> None:
    cond = spec.get("condition_expr") or spec.get("condition")
    if not cond:
        raise XamlRenderError("While requires 'condition_expr'.")
    el = ET.SubElement(parent, "While")
    el.set("DisplayName", spec.get("display_name", "While"))
    cond_el = ET.SubElement(el, "While.Condition")
    in_arg = ET.SubElement(cond_el, "InArgument")
    _set_x_attr(in_arg, "TypeArguments", "x:Boolean")
    in_arg.text = _wrap_expr(cond)
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("While"))
    body = spec.get("body") or []
    if body:
        _emit_sequence(el, {"body": body, "display_name": "Body"})


def _emit_do_while(parent: ET.Element, spec: dict) -> None:
    cond = spec.get("condition_expr") or spec.get("condition")
    if not cond:
        raise XamlRenderError("DoWhile requires 'condition_expr'.")
    el = ET.SubElement(parent, "DoWhile")
    el.set("DisplayName", spec.get("display_name", "Do While"))
    cond_el = ET.SubElement(el, "DoWhile.Condition")
    in_arg = ET.SubElement(cond_el, "InArgument")
    _set_x_attr(in_arg, "TypeArguments", "x:Boolean")
    in_arg.text = _wrap_expr(cond)
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("DoWhile"))
    _emit_sequence(el, {"body": spec.get("body") or [], "display_name": "Body"})


def _emit_for_each(parent: ET.Element, spec: dict) -> None:
    values_expr = spec.get("values_expr") or spec.get("values")
    if not values_expr:
        raise XamlRenderError("ForEach requires 'values_expr'.")
    item_name = str(spec.get("item_name", "item")).strip()
    if not _VAR_NAME_RE.match(item_name):
        raise XamlRenderError(f"ForEach 'item_name' invalid: {item_name!r}.")
    item_type = str(spec.get("item_type", "x:String")).strip() or "x:String"
    fe = ET.SubElement(parent, _qname("ui", "ForEach"))
    _set_x_attr(fe, "TypeArguments", item_type)
    fe.set("DisplayName", spec.get("display_name", f"For Each {item_name}"))
    fe.set("Values", _wrap_expr(values_expr))
    _set_sap2010_attr(fe, "WorkflowViewState.IdRef", _next_id("ForEach"))
    # UiPath ``ForEach`` expects ``ActivityAction`` under ``ui:ForEach.Body``,
    # not as a direct child (otherwise XAML loader raises ``Implementation``).
    body_host = ET.SubElement(fe, _qname("ui", "ForEach.Body"))
    action = ET.SubElement(body_host, "ActivityAction")
    _set_x_attr(action, "TypeArguments", item_type)
    arg_el = ET.SubElement(action, "ActivityAction.Argument")
    di = ET.SubElement(arg_el, "DelegateInArgument")
    _set_x_attr(di, "TypeArguments", item_type)
    di.set("Name", item_name)
    _emit_sequence(action, {"body": spec.get("body") or [], "display_name": "Body"})


def _emit_try_catch(parent: ET.Element, spec: dict) -> None:
    el = ET.SubElement(parent, "TryCatch")
    el.set("DisplayName", spec.get("display_name", "Try Catch"))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("TryCatch"))
    try_body = spec.get("try") or []
    if try_body:
        try_el = ET.SubElement(el, "TryCatch.Try")
        _emit_sequence(try_el, {"body": try_body, "display_name": "Try"})
    catches = spec.get("catches") or []
    if catches:
        catches_el = ET.SubElement(el, "TryCatch.Catches")
        for c in catches:
            exc_type = _normalize_catch_type(str(c.get("exception_type", "System.Exception")))
            var = c.get("var", "ex")
            catch = ET.SubElement(catches_el, "Catch")
            _set_x_attr(catch, "TypeArguments", exc_type)
            cact = ET.SubElement(catch, "ActivityAction")
            _set_x_attr(cact, "TypeArguments", exc_type)
            carg = ET.SubElement(cact, "ActivityAction.Argument")
            cdi = ET.SubElement(carg, "DelegateInArgument")
            _set_x_attr(cdi, "TypeArguments", exc_type)
            cdi.set("Name", var)
            _emit_sequence(cact, {"body": c.get("body") or [], "display_name": "Handler"})
    finally_body = spec.get("finally") or []
    if finally_body:
        fin_el = ET.SubElement(el, "TryCatch.Finally")
        _emit_sequence(fin_el, {"body": finally_body, "display_name": "Finally"})


def _emit_throw(parent: ET.Element, spec: dict) -> None:
    exc = spec.get("exception_expr") or spec.get("exception")
    if not exc:
        raise XamlRenderError(
            "Throw requires 'exception_expr' (e.g. "
            "'new System.Exception(\"bad\")')."
        )
    el = ET.SubElement(parent, "Throw")
    el.set("DisplayName", spec.get("display_name", "Throw"))
    el.set("Exception", _wrap_expr(exc))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("Throw"))


def _emit_invoke_workflow(parent: ET.Element, spec: dict) -> None:
    wf = spec.get("file") or spec.get("workflow")
    if not wf:
        raise XamlRenderError("InvokeWorkflow requires 'file' (relative path).")
    # Must live in the UiPath activities namespace (not the plain WF namespace),
    # otherwise Studio cannot resolve InvokeWorkflowFile / its Arguments collection.
    el = ET.SubElement(parent, _qname("ui", "InvokeWorkflowFile"))
    el.set("DisplayName", spec.get("display_name", f"Invoke {wf}"))
    el.set("WorkflowFileName", str(wf))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("InvokeWorkflowFile"))
    args = spec.get("arguments") or {}
    arg_types = spec.get("argument_types") or {}
    if args:
        args_el = ET.SubElement(el, _qname("ui", "InvokeWorkflowFile.Arguments"))
        for arg_name, binding in args.items():
            # binding format: {"direction": In|Out|InOut, "expr": "<expr>"}
            # or shorthand: "<expr>" (treated as InArgument of x:String).
            if isinstance(binding, str):
                direction = "In"
                expr = binding
            elif isinstance(binding, dict):
                direction = str(binding.get("direction", "In")).strip()
                expr = binding.get("expr") or binding.get("value") or ""
            else:
                raise XamlRenderError(
                    f"InvokeWorkflow argument '{arg_name}' has invalid binding."
                )
            if direction not in _DIRECTION_TO_ARG:
                raise XamlRenderError(
                    f"InvokeWorkflow arg '{arg_name}' direction must be "
                    f"In/Out/InOut, got {direction!r}."
                )
            type_args = str(arg_types.get(arg_name, "x:String"))
            bind_el = ET.SubElement(args_el, _DIRECTION_TO_ARG[direction])
            _set_x_attr(bind_el, "TypeArguments", type_args)
            bind_el.set(_qname("x", "Key"), arg_name)
            bind_el.text = _wrap_expr(expr)


def _emit_read_text_file(parent: ET.Element, spec: dict) -> None:
    file_name = spec.get("file_name_expr") or spec.get("file_name")
    content_var = spec.get("content_var") or spec.get("content")
    if not file_name or not content_var:
        raise XamlRenderError(
            "ReadTextFile requires 'file_name_expr' and 'content_var'."
        )
    el = ET.SubElement(parent, _qname("ui", "ReadTextFile"))
    el.set("DisplayName", spec.get("display_name", "Read Text File"))
    el.set("FileName", _wrap_expr(file_name))
    el.set("Content", _wrap_expr(content_var))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("ReadTextFile"))


def _emit_write_text_file(parent: ET.Element, spec: dict) -> None:
    file_name = spec.get("file_name_expr") or spec.get("file_name")
    text_expr = spec.get("text_expr") or spec.get("text")
    if not file_name or text_expr is None:
        raise XamlRenderError(
            "WriteTextFile requires 'file_name_expr' and 'text_expr'."
        )
    el = ET.SubElement(parent, _qname("ui", "WriteTextFile"))
    el.set("DisplayName", spec.get("display_name", "Write Text File"))
    el.set("FileName", _wrap_expr(file_name))
    el.set("Text", _wrap_expr(text_expr))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("WriteTextFile"))


def _emit_append_line(parent: ET.Element, spec: dict) -> None:
    file_name = spec.get("file_name_expr") or spec.get("file_name")
    text_expr = spec.get("text_expr") or spec.get("text")
    if not file_name or text_expr is None:
        raise XamlRenderError(
            "AppendLine requires 'file_name_expr' and 'text_expr'."
        )
    el = ET.SubElement(parent, _qname("ui", "AppendLine"))
    el.set("DisplayName", spec.get("display_name", "Append Line"))
    el.set("FileName", _wrap_expr(file_name))
    el.set("Text", _wrap_expr(text_expr))
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("AppendLine"))


def _emit_create_directory(parent: ET.Element, spec: dict) -> None:
    path_expr = spec.get("path_expr") or spec.get("path")
    if not path_expr:
        raise XamlRenderError("CreateDirectory requires 'path_expr'.")
    el = ET.SubElement(parent, "InvokeMethod")
    el.set("DisplayName", spec.get("display_name", "Create Directory"))
    el.set("MethodName", "CreateDirectory")
    # Plain ``System.IO.Directory`` is resolved in the wrong XML namespace; use
    # ``{x:Type io:Directory}`` with ``xmlns:io`` injected on the root.
    el.set("TargetType", "{x:Type io:Directory}")
    _set_sap2010_attr(el, "WorkflowViewState.IdRef", _next_id("InvokeMethod"))
    params = ET.SubElement(el, "InvokeMethod.Parameters")
    _emit_arg_element(params, "InArgument", "x:String", path_expr)


_EMITTERS = {
    "Sequence": _emit_sequence,
    "LogMessage": _emit_log_message,
    "WriteLine": _emit_write_line,
    "Assign": _emit_assign,
    "If": _emit_if,
    "While": _emit_while,
    "DoWhile": _emit_do_while,
    "ForEach": _emit_for_each,
    "TryCatch": _emit_try_catch,
    "Throw": _emit_throw,
    "InvokeWorkflow": _emit_invoke_workflow,
    "ReadTextFile": _emit_read_text_file,
    "WriteTextFile": _emit_write_text_file,
    "AppendLine": _emit_append_line,
    "CreateDirectory": _emit_create_directory,
}


# -----------------------------------------------------------------------------
# Top-level renderer
# -----------------------------------------------------------------------------


def render_xaml_workflow(
    relative_path: str,
    x_class: str = "",
    expression_language: str = "CSharp",
    namespaces: list[str] | None = None,
    references: list[str] | None = None,
    arguments: list[dict] | None = None,
    variables: list[dict] | None = None,
    body: list[dict] | None = None,
    root_kind: str = "Sequence",
) -> str:
    """Render a complete XAML workflow to a string.

    This function is public so tests and the scaffolder can call it
    directly without going through the ``@tool`` wrapper.
    """
    _reset_ids()
    if expression_language not in ("CSharp", "VisualBasic"):
        raise XamlRenderError(
            "expression_language must be 'CSharp' or 'VisualBasic'."
        )
    cls = x_class.strip() or _derive_x_class(relative_path)

    # Register prefixes before creating the root element so ET renders them.
    for pfx, uri in _PREFIXES.items():
        ET.register_namespace(pfx, uri)
    # Default namespace (activities).
    ET.register_namespace("", _NS_ACTIVITIES)

    root = ET.Element(_qname("", "Activity"))
    # Force every expected prefix to appear as xmlns:* on the root, even
    # when the workflow body doesn't happen to use that namespace as a
    # real qname (e.g. `scg:` typically appears only *inside* attribute
    # VALUES like `x:TypeArguments="scg:Dictionary(x:String, x:String)"`,
    # which ET cannot see as a namespace use). ET only emits xmlns:prefix
    # when it sees a {uri} used as an element/attribute qname somewhere,
    # so we set a namespaced attribute per prefix. ``mc:Ignorable`` is the
    # idiomatic one; for the rest we attach a harmless dummy attribute
    # that Studio ignores. The cost is a few extra empty attributes on
    # <Activity>; the win is never emitting an undeclared prefix.
    root.set(_qname("mc", "Ignorable"), "sap sap2010 sads")
    root.set(_qname("sap", "VirtualizedContainerService.HintSize"), "600,400")
    _set_sap2010_attr(root, "WorkflowViewState.IdRef", "ActivityBuilder_1")
    root.set(_qname("sads", "DebugSymbol.Symbol"), "")
    # NOTE: scg/sco/ui prefixes are force-declared on the serialized output
    # via _inject_xmlns_declarations() below, not via dummy attributes.
    # Emitting something like `scg:_=""` here produces a real XAML member
    # name `{clr-namespace:System.Collections.Generic;...}_` that Studio
    # rejects with "Cannot set unknown member" when loading the workflow.
    _set_x_attr(root, "Class", cls)

    # x:Members (arguments).
    if arguments:
        members = ET.SubElement(root, _qname("x", "Members"))
        for a in arguments:
            _validate_spec_arg(a)
            p = ET.SubElement(members, _qname("x", "Property"))
            p.set("Name", a["name"])
            p.set("Type", f"{_DIRECTION_TO_ARG[a['direction']]}({a['type']})")

    # TextExpression.NamespacesForImplementation.
    ns_el = ET.SubElement(root, "TextExpression.NamespacesForImplementation")
    ns_coll = ET.SubElement(ns_el, _qname("sco", "Collection"))
    _set_x_attr(ns_coll, "TypeArguments", "x:String")
    for n in namespaces or _DEFAULT_CSHARP_NAMESPACES:
        s = ET.SubElement(ns_coll, _qname("x", "String"))
        s.text = n

    # TextExpression.ReferencesForImplementation.
    ref_el = ET.SubElement(root, "TextExpression.ReferencesForImplementation")
    ref_coll = ET.SubElement(ref_el, _qname("sco", "Collection"))
    _set_x_attr(ref_coll, "TypeArguments", "AssemblyReference")
    for r in references or _DEFAULT_REFERENCES:
        ar = ET.SubElement(ref_coll, "AssemblyReference")
        ar.text = r

    # Body container.
    if root_kind != "Sequence":
        raise XamlRenderError(
            "Only 'Sequence' root_kind is supported in the initial release."
        )
    _emit_sequence(
        root,
        {
            "display_name": cls,
            "variables": variables or [],
            "body": body or [],
        },
    )

    ET.indent(root, space="  ")
    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    xml_text = xml_bytes.decode("utf-8")
    xml_text = _inject_xmlns_declarations(xml_text)
    return xml_text + "\n"


_XMLNS_FORCE_DECLS: tuple[tuple[str, str], ...] = (
    # Prefixes that show up only inside attribute VALUES (x:TypeArguments,
    # Property.Type, etc.) rather than as element/attribute qnames. ET does
    # not know to declare them, so we inject them textually on the root.
    ("scg", _NS_SCG),
    ("sco", _NS_SCO),
    ("s", _NS_SYS),
    ("io", _NS_IO),
    ("ui", _NS_UI),
)


def _inject_xmlns_declarations(xml_text: str) -> str:
    """Ensure scg/sco/ui xmlns declarations exist on the root <Activity>.

    ElementTree only emits ``xmlns:<prefix>`` declarations when it has seen
    the namespace used as an element or attribute qname. XAML, however,
    references these prefixes inside attribute *values* (for example
    ``x:TypeArguments="scg:Dictionary(x:String, x:String)"`` or
    ``Type="InArgument(ui:GenericValue)"``). Without an explicit
    declaration, UiPath Studio fails to load the workflow with
    ``Prefix 'scg' does not map to a namespace``.

    We used to coax ET into emitting these by setting a dummy namespaced
    attribute such as ``scg:_=""`` on the root, but that produces a real
    XAML member that Studio then rejects with
    ``Cannot set unknown member '{clr-namespace:...}_'``. Injecting the
    raw ``xmlns:*`` declarations textually side-steps both problems.
    """
    # Locate the opening ``<Activity ...>`` tag. ET emits it at or near the
    # start of the document with no preceding XML declaration.
    match = re.match(r"(\s*)<Activity\b([^>]*)>", xml_text, re.DOTALL)
    if not match:
        return xml_text
    leading, attr_text = match.group(1), match.group(2)
    start, end = match.span()

    additions: list[str] = []
    for prefix, uri in _XMLNS_FORCE_DECLS:
        if re.search(rf'\bxmlns:{re.escape(prefix)}\s*=', attr_text):
            continue
        additions.append(f'xmlns:{prefix}="{uri}"')
    if not additions:
        return xml_text

    new_attrs = attr_text.rstrip()
    new_open = f"{leading}<Activity{new_attrs} {' '.join(additions)}>"
    return xml_text[:start] + new_open + xml_text[end:]


# -----------------------------------------------------------------------------
# Validator
# -----------------------------------------------------------------------------


def _ns_strip(tag: str) -> str:
    """``{ns}local`` -> ``local`` (or ``prefix:local`` when qname visible)."""
    if tag.startswith("{"):
        # ``{uri}local``
        return tag.split("}", 1)[1]
    return tag


def validate_xaml_text(
    xaml_text: str,
    project_dir: Path | None = None,
    relative_path: str | None = None,
) -> list[XamlValidationIssue]:
    """Run the XAML linter against a string, return all issues found."""
    issues: list[XamlValidationIssue] = []

    # 1. Well-formed XML.
    try:
        root = ET.fromstring(xaml_text)
    except ET.ParseError as e:
        line, col = (None, None)
        try:
            line, col = e.position  # type: ignore[attr-defined]
        except Exception:
            pass
        issues.append(
            XamlValidationIssue(
                level="error",
                line=line,
                col=col,
                message=f"XML parsing error: {e}",
                fix=(
                    "Ensure every '<' is paired with '>', quote attribute "
                    "values, and do not write '&lt;' inside element text "
                    "that is meant to be raw XML."
                ),
            )
        )
        return issues

    root_tag = _ns_strip(root.tag)
    if root_tag != "Activity":
        issues.append(
            XamlValidationIssue(
                level="error",
                line=None,
                col=None,
                message=f"Root element must be <Activity>, got <{root_tag}>.",
                fix="Wrap the workflow in <Activity xmlns='...'> ...</Activity>.",
            )
        )
        return issues

    # 2. x:Class present and matches path.
    x_class = root.get(_qname("x", "Class"))
    if not x_class:
        issues.append(
            XamlValidationIssue(
                level="error",
                line=None,
                col=None,
                message="Root <Activity> is missing x:Class.",
                fix=(
                    "Add x:Class to <Activity> matching the file path, "
                    "e.g. 'Workflows_ExtractInvoice' for "
                    "Workflows/ExtractInvoice.xaml."
                ),
            )
        )
    elif relative_path:
        expected = _derive_x_class(relative_path)
        if x_class != expected:
            issues.append(
                XamlValidationIssue(
                    level="error",
                    line=None,
                    col=None,
                    message=(
                        f"x:Class='{x_class}' does not match path "
                        f"'{relative_path}'."
                    ),
                    fix=f"Set x:Class='{expected}'.",
                )
            )

    # 3. Required namespaces on root.
    # ``ET`` stores them as ``{uri}local`` in children, but the root's own
    # attrib dict does NOT retain xmlns declarations. Instead, check that
    # known children use the expected namespaces. A simple heuristic: look
    # at the serialized output for xmlns:x and xmlns:sap2010.
    for required in ("xmlns:x", "xmlns:sap2010"):
        # The only reliable way: re-find xmlns declarations in the source.
        if required not in xaml_text:
            issues.append(
                XamlValidationIssue(
                    level="warning",
                    line=None,
                    col=None,
                    message=f"Root <Activity> is missing {required}.",
                    fix=f"Add {required} declaration to <Activity>.",
                )
            )

    # Index every <Assign> to check 4 + 5.
    for assign in root.iter():
        tag = _ns_strip(assign.tag)
        display = assign.get("DisplayName") or "<unnamed>"

        if tag == "Assign":
            to_el = assign.find(_qname("", "Assign.To"))
            val_el = assign.find(_qname("", "Assign.Value"))
            if to_el is None or not list(to_el):
                issues.append(
                    XamlValidationIssue(
                        level="error",
                        line=None,
                        col=None,
                        message=(
                            f"Assign '{display}' is missing Assign.To or its "
                            "OutArgument child."
                        ),
                        fix=(
                            "Add <Assign.To><OutArgument "
                            "x:TypeArguments='x:String'>[target]</OutArgument>"
                            "</Assign.To>."
                        ),
                    )
                )
            else:
                target = list(to_el)[0]
                if not (target.text or "").strip():
                    issues.append(
                        XamlValidationIssue(
                            level="error",
                            line=None,
                            col=None,
                            message=(
                                f"Assign '{display}' has empty Assign.To - "
                                "no target variable bound."
                            ),
                            fix=(
                                "Set the OutArgument text to a variable "
                                "reference, e.g. [myVar]."
                            ),
                        )
                    )
            if val_el is None or not list(val_el):
                issues.append(
                    XamlValidationIssue(
                        level="error",
                        line=None,
                        col=None,
                        message=(
                            f"Assign '{display}' is missing Assign.Value or "
                            "its InArgument child."
                        ),
                        fix=(
                            "Add <Assign.Value><InArgument "
                            "x:TypeArguments='x:String'>[\"\"]</InArgument>"
                            "</Assign.Value>."
                        ),
                    )
                )
            else:
                val = list(val_el)[0]
                if not (val.text or "").strip():
                    issues.append(
                        XamlValidationIssue(
                            level="error",
                            line=None,
                            col=None,
                            message=(
                                f"Assign '{display}' has empty Assign.Value."
                            ),
                            fix="Provide a non-empty InArgument expression.",
                        )
                    )

        if tag == "Throw":
            exc = assign.get("Exception")
            if not (exc or "").strip():
                issues.append(
                    XamlValidationIssue(
                        level="error",
                        line=None,
                        col=None,
                        message=f"Throw '{display}' has empty Exception.",
                        fix=(
                            "Set Exception=\"[new System.Exception(\\\"...\\\")]\"."
                        ),
                    )
                )

        if tag == "If":
            cond = assign.get("Condition")
            if not (cond or "").strip():
                cond_el = assign.find(_qname("", "If.Condition"))
                if cond_el is not None:
                    in_arg = cond_el.find(_qname("", "InArgument"))
                    if in_arg is not None and (in_arg.text or "").strip():
                        cond = in_arg.text
            if not (cond or "").strip():
                issues.append(
                    XamlValidationIssue(
                        level="error",
                        line=None,
                        col=None,
                        message=f"If '{display}' has empty Condition.",
                        fix=(
                            "Set Condition=\"[<bool>]\" or add "
                            "<If.Condition><InArgument x:TypeArguments=\"x:Boolean\">"
                            "[expr]</InArgument></If.Condition>."
                        ),
                    )
                )

        if tag == "InvokeWorkflowFile":
            wf = assign.get("WorkflowFileName")
            if wf and project_dir is not None:
                target = (project_dir / wf).resolve()
                if not target.exists():
                    issues.append(
                        XamlValidationIssue(
                            level="warning",
                            line=None,
                            col=None,
                            message=(
                                f"InvokeWorkflow '{display}' references "
                                f"missing file: {wf}"
                            ),
                            fix=(
                                "Create the referenced workflow first, or "
                                "correct the WorkflowFileName path."
                            ),
                        )
                    )

    # 6. IdRef consistency: either all have IdRef or none do.
    id_key = _qname("sap2010", "WorkflowViewState.IdRef")
    act_names = {
        "Sequence", "Assign", "If", "While", "DoWhile", "TryCatch",
        "Throw", "InvokeWorkflowFile", "WriteLine", "InvokeMethod",
        "LogMessage", "ReadTextFile", "WriteTextFile", "AppendLine",
        "ForEach",
    }
    have_id = 0
    miss_id = 0
    for el in root.iter():
        name = _ns_strip(el.tag)
        if name not in act_names:
            continue
        if el.get(id_key):
            have_id += 1
        else:
            miss_id += 1
    if have_id and miss_id:
        issues.append(
            XamlValidationIssue(
                level="warning",
                line=None,
                col=None,
                message=(
                    f"{miss_id} activities missing sap2010:WorkflowViewState.IdRef "
                    f"while {have_id} have one (inconsistent)."
                ),
                fix=(
                    "Give every activity a unique IdRef, or remove all of "
                    "them. Mixed state breaks the Studio designer view."
                ),
            )
        )

    # 7. x:Members argument type shape.
    members = root.find(_qname("x", "Members"))
    if members is not None:
        for prop in members.findall(_qname("x", "Property")):
            t = prop.get("Type") or ""
            if not re.match(r"^(In|Out|InOut)Argument\(.+\)$", t):
                issues.append(
                    XamlValidationIssue(
                        level="error",
                        line=None,
                        col=None,
                        message=(
                            f"Argument '{prop.get('Name')}' has malformed "
                            f"Type='{t}'."
                        ),
                        fix=(
                            "Use InArgument(x:String), "
                            "OutArgument(scg:Dictionary(x:String, x:String)), "
                            "etc."
                        ),
                    )
                )

    return issues


def _format_issues(issues: list[XamlValidationIssue], relative_path: str) -> str:
    if not issues:
        return "0 errors, 0 warnings"
    lines = []
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    for i in issues:
        loc = ""
        if i.line is not None:
            loc = f":{i.line}" + (f":{i.col}" if i.col is not None else "")
        lines.append(
            f"  [{i.level.upper()}] {relative_path}{loc}\n"
            f"    {i.message}\n"
            f"    Fix: {i.fix}"
        )
    return (
        f"{len(errors)} errors, {len(warnings)} warnings\n"
        + "\n".join(lines)
    )


# -----------------------------------------------------------------------------
# Path resolution
# -----------------------------------------------------------------------------


def _resolve_project_dir(project_dir: str) -> tuple[Path | None, str | None]:
    if not project_dir or not str(project_dir).strip():
        return None, "project_dir is required and must be an absolute path."
    p = Path(project_dir).expanduser()
    if not p.is_absolute():
        return None, (
            f"project_dir must be an absolute path, got {project_dir!r}. "
            "Pass the full path to the UiPath project directory."
        )
    if not p.exists():
        return None, f"project_dir does not exist: {p}"
    if not (p / "project.json").exists():
        return None, (
            f"No project.json in project_dir: {p}. "
            "Run ensure_project_structure or create_project first."
        )
    return p, None


def _tool_ok(msg: str) -> str:
    return ToolOutcome(ok=True, message=msg).to_text()


def _tool_err(msg: str) -> str:
    return ToolOutcome(ok=False, message=msg).to_text()


# -----------------------------------------------------------------------------
# Public tools
# -----------------------------------------------------------------------------


@tool
def create_xaml_workflow(
    project_dir: str,
    relative_path: str,
    body: list[dict],
    x_class: str = "",
    expression_language: str = "CSharp",
    arguments: list[dict] | None = None,
    variables: list[dict] | None = None,
    namespaces: list[str] | None = None,
    references: list[str] | None = None,
) -> str:
    """Render a classic RPA XAML workflow from a structured spec and write it.

    This is the preferred way to create XAML for UiPath Studio projects.
    The agent never has to hand-emit XML -- pass a list of typed activity
    records and the tool guarantees valid XAML (namespaces, x:Class,
    IdRefs, argument/variable binding, XML escaping). The resulting file is
    linted by ``validate_xaml`` before the tool returns.

    Args:
        project_dir: Absolute path to the UiPath project directory
            (the directory containing project.json).
        relative_path: Path of the .xaml file relative to project_dir,
            using forward or backward slashes (e.g.
            "Workflows/ExtractInvoice.xaml"). The directory will be
            created if missing.
        body: Ordered list of activity records. Each record is a dict
            with a "kind" key. Supported kinds:

            - {"kind": "LogMessage", "level": "Info"|"Warn"|"Error",
               "message_expr": "<C# expr>"}
            - {"kind": "WriteLine", "text_expr": "<C# expr>"}
            - {"kind": "Assign", "to": "<variable_name>",
               "to_type": "x:String" (optional),
               "to_direction": "Out"|"InOut" (optional, default Out),
               "value_expr": "<C# expr>"}
            - {"kind": "If", "condition_expr": "<bool>",
               "then": [...], "else": [...]}
            - {"kind": "While"|"DoWhile", "condition_expr": "<bool>",
               "body": [...]}
            - {"kind": "ForEach", "item_name": "x", "item_type": "x:String",
               "values_expr": "<IEnumerable expr>", "body": [...]}
            - {"kind": "TryCatch", "try": [...],
               "catches": [{"exception_type": "System.Exception",
                            "var": "ex", "body": [...]}],
               "finally": [...]}
            - {"kind": "Throw", "exception_expr": "<C# expr>"}
            - {"kind": "InvokeWorkflow", "file": "Workflows/Sub.xaml",
               "arguments": {"in_X": "<expr>",
                             "out_Y": {"direction": "Out", "expr": "target"}},
               "argument_types": {"in_X": "x:String", ...}}
            - {"kind": "ReadTextFile", "file_name_expr": "<expr>",
               "content_var": "<variable_name>"}
            - {"kind": "WriteTextFile"|"AppendLine",
               "file_name_expr": "<expr>", "text_expr": "<expr>"}
            - {"kind": "CreateDirectory", "path_expr": "<expr>"}

        x_class: Value for x:Class. Defaults to deriving from
            relative_path (e.g. "Workflows/Extract.xaml" ->
            "Workflows_Extract").
        expression_language: "CSharp" (default) or "VisualBasic".
        arguments: Workflow arguments for <x:Members>. Each entry:
            {"name": "in_FilePath", "direction": "In"|"Out"|"InOut",
             "type": "x:String"}. Names must start with in_/out_/io_.
        variables: Local variables for the root Sequence. Each entry:
            {"name": "rawText", "type": "x:String",
             "default": "<C# expr>" (optional)}.
        namespaces: Override the default C# namespaces imported into
            the workflow. Leave None for the sensible default set.
        references: Override the default assembly references. Leave
            None for the default set.

    Returns:
        "[OK] Wrote <abs_path> (<bytes>). Validator: 0 errors, 0 warnings."
        on success, or an actionable "[ERROR]" message. When the
        validator reports issues, the file is still written so the
        agent can inspect it, but the tool returns an error status.
    """
    proj, err = _resolve_project_dir(project_dir)
    if err is not None or proj is None:
        return _tool_err(err or "Invalid project_dir.")

    try:
        xaml_text = render_xaml_workflow(
            relative_path=relative_path,
            x_class=x_class,
            expression_language=expression_language,
            namespaces=namespaces,
            references=references,
            arguments=arguments,
            variables=variables,
            body=body,
        )
    except XamlRenderError as e:
        return _tool_err(f"Spec error: {e}")
    except Exception as e:
        return _tool_err(
            f"Unexpected render failure ({type(e).__name__}): {e}. "
            "Re-check activity spec shape."
        )

    # Normalize path.
    rel = relative_path.replace("\\", "/").lstrip("/")
    dest = (proj / rel).resolve()
    try:
        dest.relative_to(proj.resolve())
    except ValueError:
        return _tool_err(
            f"relative_path '{relative_path}' escapes project_dir. Refusing."
        )
    if not dest.name.lower().endswith(".xaml"):
        return _tool_err(
            f"relative_path must end with .xaml, got {relative_path!r}."
        )

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(xaml_text, encoding="utf-8")
    except OSError as e:
        return _tool_err(f"Could not write {dest}: {e}")

    issues = validate_xaml_text(xaml_text, project_dir=proj, relative_path=rel)
    summary = _format_issues(issues, rel)
    size = dest.stat().st_size

    if any(i.level == "error" for i in issues):
        return _tool_err(
            f"Wrote {dest} ({size} bytes) but validation failed:\n{summary}"
        )
    return _tool_ok(f"Wrote {dest} ({size} bytes). Validator: {summary}")


@tool
def validate_xaml(project_dir: str, relative_path: str) -> str:
    """Lint a XAML workflow on disk and return precise, actionable issues.

    Unlike the write_file embedded XML check, this tool inspects UiPath
    workflow semantics: x:Class shape, Assign.To/Value binding,
    WorkflowViewState.IdRef consistency, Throw/If empty fields, and
    InvokeWorkflow target existence.

    Args:
        project_dir: Absolute path to the UiPath project directory.
        relative_path: Path to the .xaml file relative to project_dir.

    Returns:
        "[OK] 0 errors, 0 warnings" when clean, or an "[ERROR]" report
        listing each issue with file, location, message, and fix hint.
    """
    proj, err = _resolve_project_dir(project_dir)
    if err is not None or proj is None:
        return _tool_err(err or "Invalid project_dir.")

    rel = relative_path.replace("\\", "/").lstrip("/")
    target = (proj / rel).resolve()
    try:
        target.relative_to(proj.resolve())
    except ValueError:
        return _tool_err(
            f"relative_path '{relative_path}' escapes project_dir."
        )
    if not target.exists():
        return _tool_err(f"File not found: {target}")

    try:
        xaml_text = target.read_text(encoding="utf-8")
    except OSError as e:
        return _tool_err(f"Could not read {target}: {e}")

    issues = validate_xaml_text(xaml_text, project_dir=proj, relative_path=rel)
    summary = _format_issues(issues, rel)
    if any(i.level == "error" for i in issues):
        return _tool_err(f"Validation failed:\n{summary}")
    return _tool_ok(f"Validator: {summary}")


def get_xaml_tools() -> list:
    """Return the XAML authoring tools in discovery order."""
    return [create_xaml_workflow, validate_xaml]
