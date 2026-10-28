package com.neon.play.simulator;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.util.Log;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.webkit.JavascriptInterface;
import android.webkit.JsPromptResult;
import android.webkit.JsResult;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Set;

/** Offline-only application shell. No INTERNET permission, accounts or real-money endpoints. */
public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String PREFIX = "https://" + HOST + "/assets/web/";
    private static final int IMPORT_REQUEST = 301;
    private static final int EXPORT_REQUEST = 302;
    private static final int MAX_BACKUP_CHARS = 2_000_000;
    private static final Set<String> ASSETS = new HashSet<>(Arrays.asList(
            "index.html", "app.js", "app.css", "icon.svg", "icon-192.png",
            "icon-512.png", "manifest.webmanifest", "sw.js"));

    private WebView webView;
    private ValueCallback<Uri[]> fileChooser;
    private String exportContents;
    private int rendererRestarts;
    private boolean destroyed;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(7, 11, 22));
        getWindow().setNavigationBarColor(Color.rgb(7, 11, 22));
        buildWebView();
    }

    private void buildWebView() {
        if (destroyed) return;
        try {
            WebView view = new WebView(this);
            webView = view;
            view.setBackgroundColor(Color.rgb(7, 11, 22));
            view.setOverScrollMode(View.OVER_SCROLL_NEVER);
            WebSettings settings = view.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setAllowFileAccess(false);
            // Android document picker needs access to the selected content:// URI.
            settings.setAllowContentAccess(true);
            settings.setAllowFileAccessFromFileURLs(false);
            settings.setAllowUniversalAccessFromFileURLs(false);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
            settings.setJavaScriptCanOpenWindowsAutomatically(false);
            settings.setSupportMultipleWindows(false);
            // No page other than our signed, bundled resources can be loaded.
            view.addJavascriptInterface(new BackupBridge(), "NeonBridge");
            view.setWebViewClient(new LocalClient());
            view.setWebChromeClient(new DialogsAndFiles());
            setContentView(view);
            view.loadUrl(PREFIX + "index.html");
        } catch (RuntimeException ex) {
            showError("Не удалось запустить Android WebView.");
        }
    }

    private static WebResourceResponse textResponse(int status, String text) {
        WebResourceResponse r = new WebResourceResponse("text/plain", "UTF-8",
                new ByteArrayInputStream(text.getBytes(StandardCharsets.UTF_8)));
        r.setStatusCodeAndReasonPhrase(status, status == 200 ? "OK" : "Not Found");
        HashMap<String, String> headers = new HashMap<>();
        headers.put("Cache-Control", "no-store");
        headers.put("X-Content-Type-Options", "nosniff");
        r.setResponseHeaders(headers);
        return r;
    }

    private static boolean isBundled(Uri uri) {
        return uri != null && "https".equals(uri.getScheme()) && HOST.equals(uri.getHost())
                && uri.getPath() != null && uri.getPath().startsWith("/assets/web/")
                && ASSETS.contains(uri.getPath().substring("/assets/web/".length()));
    }

    private final class LocalClient extends WebViewClient {
        @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
            return !isBundled(request.getUrl());
        }
        @Override public boolean shouldOverrideUrlLoading(WebView view, String url) {
            return !isBundled(Uri.parse(url));
        }
        @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
            Uri uri = request.getUrl();
            if (uri != null && "https".equals(uri.getScheme()) && HOST.equals(uri.getHost())
                    && "/__ping".equals(uri.getPath())) return textResponse(200, "ok");
            if (!isBundled(uri)) return textResponse(404, "Offline resource not available");
            String filename = uri.getPath().substring("/assets/web/".length());
            String mime = "application/octet-stream";
            if (filename.endsWith(".html")) mime = "text/html";
            else if (filename.endsWith(".js")) mime = "text/javascript";
            else if (filename.endsWith(".css")) mime = "text/css";
            else if (filename.endsWith(".png")) mime = "image/png";
            else if (filename.endsWith(".svg")) mime = "image/svg+xml";
            else if (filename.endsWith(".json") || filename.endsWith(".webmanifest")) mime = "application/json";
            try {
                InputStream input = getAssets().open("web/" + filename);
                WebResourceResponse response = new WebResourceResponse(mime, "UTF-8", input);
                HashMap<String, String> headers = new HashMap<>();
                headers.put("X-Content-Type-Options", "nosniff");
                // Avoid stale UI or old wallet logic surviving an application update.
                headers.put("Cache-Control", filename.endsWith(".png") ? "private, max-age=86400" : "no-store");
                response.setResponseHeaders(headers);
                return response;
            } catch (IOException ex) {
                return textResponse(404, "Missing bundled game resource: " + filename);
            }
        }
        @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
            if (request.isForMainFrame()) showError("Не удалось открыть встроенные игровые файлы.");
        }
        @Override public void onPageFinished(WebView view, String url) {
            if (webView != view || destroyed || !isBundled(Uri.parse(url))
                    || !url.endsWith("/index.html")) return;
            // An older WebView can finish the document before its game JS is initialized.
            // Give it a bounded chance to become ready instead of showing a false crash.
            verifyGameReady(view, 12);
        }
        @Override public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
            // Never reuse a WebView after its renderer process has died.
            if (webView != view) return true;
            webView = null;
            if (fileChooser != null) { fileChooser.onReceiveValue(null); fileChooser = null; }
            view.destroy();
            if (!destroyed && rendererRestarts++ < 1) buildWebView();
            else showError("Игровой движок остановился. Прогресс предыдущих ставок хранится локально.");
            return true;
        }
    }

    private void verifyGameReady(WebView view, int attemptsLeft) {
        view.postDelayed(() -> {
            if (webView != view || destroyed) return;
            view.evaluateJavascript("Boolean(window.NEON_INFO && window.NEON_INFO.version === '1.7.8' && window.NEON_INFO.gameCount === 44)", result -> {
                if (webView != view || destroyed) return;
                if ("true".equals(result)) {
                    Log.i("NEON_QA", "WEB_READY_v1.7.8_games44");
                } else if (attemptsLeft > 1) {
                    verifyGameReady(view, attemptsLeft - 1);
                } else {
                    Log.e("NEON_QA", "GAME_STARTUP_FAILED");
                    showError("Игровые ресурсы загрузились не полностью. Попробуй перезапуск.");
                }
            });
        }, 600);
    }

    private void showError(String message) {
        if (destroyed || isFinishing()) return;
        runOnUiThread(() -> {
            if (destroyed || isFinishing()) return;
            LinearLayout layout = new LinearLayout(this);
            layout.setOrientation(LinearLayout.VERTICAL);
            layout.setPadding(32, 48, 32, 32);
            layout.setBackgroundColor(Color.rgb(7, 11, 22));
            TextView label = new TextView(this);
            label.setText("NEON CASINO\n\n" + message + "\n\nВсе фишки виртуальные; сохранённый прогресс не сбрасывается.");
            label.setTextColor(Color.WHITE);
            label.setTextSize(18);
            layout.addView(label);
            Button retry = new Button(this);
            retry.setText("ПОВТОРИТЬ ЗАПУСК");
            retry.setOnClickListener(v -> {
                WebView old = webView;
                webView = null;
                if (old != null) old.destroy();
                rendererRestarts = 0;
                buildWebView();
            });
            layout.addView(retry);
            setContentView(layout);
        });
    }

    private final class DialogsAndFiles extends WebChromeClient {
        @Override public boolean onJsAlert(WebView view, String url, String message, JsResult result) {
            new AlertDialog.Builder(MainActivity.this).setMessage(message)
                    .setPositiveButton("OK", (dialog, which) -> result.confirm())
                    .setOnCancelListener(dialog -> result.cancel()).show();
            return true;
        }
        @Override public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
            new AlertDialog.Builder(MainActivity.this).setMessage(message)
                    .setPositiveButton("Да", (dialog, which) -> result.confirm())
                    .setNegativeButton("Отмена", (dialog, which) -> result.cancel())
                    .setOnCancelListener(dialog -> result.cancel()).show();
            return true;
        }
        @Override public boolean onJsPrompt(WebView view, String url, String message,
                                            String defaultValue, JsPromptResult result) {
            android.widget.EditText input = new android.widget.EditText(MainActivity.this);
            input.setText(defaultValue);
            new AlertDialog.Builder(MainActivity.this).setMessage(message).setView(input)
                    .setPositiveButton("OK", (dialog, which) -> result.confirm(input.getText().toString()))
                    .setNegativeButton("Отмена", (dialog, which) -> result.cancel())
                    .setOnCancelListener(dialog -> result.cancel()).show();
            return true;
        }
        @Override public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                                    FileChooserParams params) {
            if (fileChooser != null) fileChooser.onReceiveValue(null);
            fileChooser = callback;
            Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
            picker.addCategory(Intent.CATEGORY_OPENABLE);
            picker.setType("application/json");
            try { startActivityForResult(picker, IMPORT_REQUEST); return true; }
            catch (Exception ex) {
                fileChooser.onReceiveValue(null);
                fileChooser = null;
                return true;
            }
        }
    }

    private final class BackupBridge {
        @JavascriptInterface public void saveBackup(String json) {
            if (json == null || json.length() > MAX_BACKUP_CHARS) {
                backupResult(false);
                return;
            }
            runOnUiThread(() -> {
                if (destroyed || exportContents != null) { backupResult(false); return; }
                exportContents = json;
                Intent picker = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                picker.addCategory(Intent.CATEGORY_OPENABLE);
                picker.setType("application/json");
                picker.putExtra(Intent.EXTRA_TITLE, "neon-casino-save.json");
                try { startActivityForResult(picker, EXPORT_REQUEST); }
                catch (Exception ex) { exportContents = null; backupResult(false); }
            });
        }
    }

    private void backupResult(boolean success) {
        runOnUiThread(() -> {
            if (webView != null && !destroyed) {
                webView.evaluateJavascript("window.neonNativeBackupComplete && window.neonNativeBackupComplete(" + success + ")", null);
            }
        });
    }

    @Override protected void onActivityResult(int request, int resultCode, Intent data) {
        super.onActivityResult(request, resultCode, data);
        if (request == IMPORT_REQUEST) {
            ValueCallback<Uri[]> callback = fileChooser;
            fileChooser = null;
            if (callback != null) {
                Uri chosen = resultCode == RESULT_OK && data != null ? data.getData() : null;
                callback.onReceiveValue(chosen == null ? null : new Uri[]{chosen});
            }
        } else if (request == EXPORT_REQUEST) {
            String payload = exportContents;
            exportContents = null;
            boolean written = false;
            if (payload != null && resultCode == RESULT_OK && data != null && data.getData() != null) {
                try (OutputStream stream = getContentResolver().openOutputStream(data.getData(), "w")) {
                    if (stream != null) {
                        stream.write(payload.getBytes(StandardCharsets.UTF_8));
                        stream.flush();
                        written = true;
                    }
                } catch (Exception ignored) {
                    written = false;
                }
            }
            backupResult(written);
        }
    }

    @Override public void onBackPressed() {
        if (webView == null) { super.onBackPressed(); return; }
        webView.evaluateJavascript("(function(){if(typeof state!=='undefined'&&state.modal){state.modal=null;renderModal();return true;}" +
                "var side=document.querySelector('.sidebar');var shade=document.querySelector('.mobile-nav-backdrop');" +
                "if(side&&side.classList.contains('open')){if(typeof setMobileNav==='function')setMobileNav(false);else{side.classList.remove('open');if(shade)shade.classList.remove('show');document.body.classList.remove('nav-visible');}return true;}" +
                "return false})()", value -> {
            if (!"true".equals(value) && !isFinishing()) {
                new AlertDialog.Builder(this).setMessage("Закрыть NEON CASINO?")
                        .setPositiveButton("Закрыть", (d, w) -> finish())
                        .setNegativeButton("Играть", null).show();
            }
        });
    }

    @Override protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }
    @Override protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }
    @Override protected void onDestroy() {
        destroyed = true;
        if (fileChooser != null) { fileChooser.onReceiveValue(null); fileChooser = null; }
        if (webView != null) { webView.destroy(); webView = null; }
        super.onDestroy();
    }
}
