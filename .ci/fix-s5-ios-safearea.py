#!/usr/bin/env python3
"""Keep the WebView below the iPhone status bar / Dynamic Island."""
from pathlib import Path

p = Path("s5platform/ios/NEONROYALE/NeonCasinoApp.swift")
s = p.read_text(encoding="utf-8")
old = """            NeonWebView()
                .ignoresSafeArea()"""
new = """            NeonWebView()
                .background(
                    Color(red: 7.0 / 255.0, green: 11.0 / 255.0, blue: 22.0 / 255.0)
                        .ignoresSafeArea()
                )"""
if s.count(old) != 1:
    raise SystemExit("Unexpected SwiftUI view code, refusing automatic patch")
p.write_text(s.replace(old, new), encoding="utf-8")
assert ".ignoresSafeArea()" not in s.replace(old, new).split("NeonWebView()",1)[1].split(".background(",1)[0]
print("PASS: WebView respects safe area; only the background extends to screen edges")
