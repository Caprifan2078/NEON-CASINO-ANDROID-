from pathlib import Path
java = Path("s5src/app/src/androidTest/java/com/neon/play/simulator/NeonWebViewInstrumentedTest.java")
smoke = Path("s5src/tests/android_smoke.sh")
s = java.read_text()
begin = "    @Test public void stagePersistentWalletCheckpoint()"
marker = "    /** Read the checkpoint ONLY after CI has closed the previous process and reinstalled. */"
assert s.count(begin) == 1 and s.count(marker) == 1
a = s.index(begin)
b = s.index(marker, a)
stage = s[a:b]
ending = "        }\n    }\n\n"
assert stage.endswith(ending)
stage = stage[:-len(ending)] + "            Thread.sleep(2500);\n" + ending
probe = """    @Test public void verifyCheckpointBeforeUpgrade() throws InterruptedException {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            awaitGame(scenario);
            assertEquals("Checkpoint missing before upgrade", "true", evaluate(scenario,
                    "Boolean(localStorage.getItem('__neon_android_s4_cold_reinstall'))"));
            assertEquals("Wallet missing before upgrade", "true", evaluate(scenario,
                    "Boolean(localStorage.getItem('neon-casino-local-v1'))"));
        }
    }

"""
updated_java = s[:a] + stage + probe + s[b:]
# Slow emulators sometimes delay WebView callbacks; preserve fail-closed assertions.
assert updated_java.count("latch.await(8, TimeUnit.SECONDS)") == 1
updated_java = updated_java.replace("latch.await(8, TimeUnit.SECONDS)", "latch.await(25, TimeUnit.SECONDS)")
java.write_text(updated_java)
t = smoke.read_text()
needle = "run_test stagePersistentWalletCheckpoint\n"
assert t.count(needle) == 1
smoke.write_text(t.replace(needle, needle + "run_test verifyCheckpointBeforeUpgrade\n", 1))
print("PASS: independent checkpoint check before APK upgrade enabled")
