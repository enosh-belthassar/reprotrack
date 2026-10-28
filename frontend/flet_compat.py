"""Compatibility layer for Flet 1.0+ runtime."""

import flet as ft

# 1. Colors
if not hasattr(ft, "colors"):
    ft.colors = ft.Colors

# 2. Geometry helpers (Padding, Margin, BorderRadius, Border)
for attr in ["all", "symmetric", "only", "zero"]:
    if hasattr(ft.Padding, attr) and not hasattr(ft.padding, attr):
        setattr(ft.padding, attr, getattr(ft.Padding, attr))
    if hasattr(ft.Margin, attr) and not hasattr(ft.margin, attr):
        setattr(ft.margin, attr, getattr(ft.Margin, attr))

for attr in ["all", "only", "horizontal", "vertical"]:
    if hasattr(ft.BorderRadius, attr) and not hasattr(ft.border_radius, attr):
        setattr(ft.border_radius, attr, getattr(ft.BorderRadius, attr))

for attr in ["all", "only", "symmetric"]:
    if hasattr(ft.Border, attr) and not hasattr(ft.border, attr):
        setattr(ft.border, attr, getattr(ft.Border, attr))

for attr in [
    "CENTER",
    "TOP_LEFT",
    "TOP_CENTER",
    "TOP_RIGHT",
    "CENTER_LEFT",
    "CENTER_RIGHT",
    "BOTTOM_LEFT",
    "BOTTOM_CENTER",
    "BOTTOM_RIGHT",
]:
    val = getattr(ft.Alignment, attr, None)
    if val is not None:
        setattr(ft.alignment, attr.lower(), val)
        setattr(ft.alignment, attr, val)


# 3. Button wrappers for Flet 1.0 (where content replaces text)
def _wrap_btn(btn_cls):
    def wrapper(*args, **kwargs):
        if "text" in kwargs:
            kwargs["content"] = kwargs.pop("text")
        return btn_cls(*args, **kwargs)

    return wrapper


if hasattr(ft, "FilledButton"):
    ft.ElevatedButton = _wrap_btn(ft.FilledButton)
if hasattr(ft, "OutlinedButton"):
    ft.OutlinedButton = _wrap_btn(ft.OutlinedButton)
if hasattr(ft, "TextButton"):
    ft.TextButton = _wrap_btn(ft.TextButton)


# 4. Safe Control.update() when control is not yet mounted to page
_orig_control_update = ft.Control.update


def _safe_control_update(self, *args, **kwargs):
    try:
        if self.page is not None:
            return _orig_control_update(self, *args, **kwargs)
    except RuntimeError:
        return None


ft.Control.update = _safe_control_update
