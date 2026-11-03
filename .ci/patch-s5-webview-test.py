#!/usr/bin/env python3
"""Split the synchronous 44-game WebView stress loop into 44 bounded tasks.

On a slower Android emulator, issuing 44 clicks from a single evaluateJavascript
call blocks the renderer and can time out the callback. Retain all assertions.
"""
from pathlib import Path

path = Path('s5src/app/src/androidTest/java/com/neon/play/simulator/NeonWebViewInstrumentedTest.java')
s = path.read_text(encoding='utf-8')
start_marker = '            assertEquals("true", evaluate(scenario,\n                    "(function(){var navs='
end_marker = '            // Persist a real snapshot, then compare the wallet against disk after restart.'
if s.count(start_marker) != 1 or s.count(end_marker) != 1:
    raise SystemExit('Unexpected instrumentation source — refusing to patch blindly')
start = s.index(start_marker)
end = s.index(end_marker, start)
replacement = '''            // Each click runs in a separate WebView event-loop task.
            // Verify all 44 panels and that navigation never changes the wallet.
            String walletBeforeNavigation = evaluate(scenario, "String(state.balance)");
            assertEquals("true", evaluate(scenario,
                    "document.querySelectorAll('#gameNav [data-action=nav]').length===44"));
            for (int i = 0; i < 44; i++) {
                String js = "(function(){var nav=document.querySelectorAll(" +
                        "'#gameNav [data-action=nav]')[" + i + "];" +
                        "if(!nav)return false;var id=nav.dataset.game;" +
                        "nav.click();return Boolean(state.game===id&&" +
                        "document.querySelector('#gameArea').children.length);})()";
                assertEquals("Game panel navigation at index " + i,
                        "true", evaluate(scenario, js));
            }
            assertEquals(walletBeforeNavigation, evaluate(scenario, "String(state.balance)"));
'''
path.write_text(s[:start] + replacement + s[end:], encoding='utf-8')
print('PASS: instrumented 44-game navigation split into bounded WebView calls')
